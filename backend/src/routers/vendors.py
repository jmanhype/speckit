"""
Vendor API routes

Endpoints for vendor account management and GDPR compliance.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.vendor import Vendor
from src.services.gdpr_service import GDPRService
from src.services.audit_service import AuditService
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/vendors", tags=["vendors"])


class VendorResponse(BaseModel):
    """Vendor profile response"""
    id: UUID
    email: EmailStr
    business_name: str
    phone: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class VendorUpdateRequest(BaseModel):
    """Vendor profile update request"""
    business_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class DeleteAccountRequest(BaseModel):
    """Account deletion request"""
    confirm_email: EmailStr
    reason: Optional[str] = None


@router.get("/me", response_model=VendorResponse)
def get_current_vendor_profile(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> VendorResponse:
    """
    Get current vendor profile

    Args:
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        Vendor profile
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    return VendorResponse.model_validate(vendor)


@router.patch("/me", response_model=VendorResponse)
def update_vendor_profile(
    update_data: VendorUpdateRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> VendorResponse:
    """
    Update current vendor profile

    Args:
        update_data: Profile update fields
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        Updated vendor profile
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    # Store old values for audit
    old_values = {
        "business_name": vendor.business_name,
        "phone": vendor.phone,
        "email": vendor.email,
    }

    # Update fields
    if update_data.business_name is not None:
        vendor.business_name = update_data.business_name

    if update_data.phone is not None:
        vendor.phone = update_data.phone

    if update_data.email is not None:
        vendor.email = update_data.email

    db.commit()
    db.refresh(vendor)

    # Log update
    audit_service = AuditService(db)
    audit_service.log_action(
        vendor_id=str(vendor_id),
        action="UPDATE",
        user_id=str(vendor_id),
        user_email=vendor.email,
        resource_type="vendor",
        resource_id=str(vendor.id),
        old_values=old_values,
        new_values={
            "business_name": vendor.business_name,
            "phone": vendor.phone,
            "email": vendor.email,
        },
        changes_summary="Vendor profile updated",
    )

    logger.info(f"Vendor {vendor_id} updated profile")

    return VendorResponse.model_validate(vendor)


@router.get("/me/data-export")
async def export_vendor_data(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Export all vendor data (GDPR Article 15 - Right to access)

    Returns complete data package in machine-readable JSON format
    containing all personal data, products, sales, recommendations, etc.

    Args:
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        Complete data export as JSON
    """
    gdpr_service = GDPRService(db)

    try:
        # Generate data export
        data_package = gdpr_service.export_user_data(str(vendor_id))

        # Log data access
        audit_service = AuditService(db)
        audit_service.log_action(
            vendor_id=str(vendor_id),
            action="GDPR_EXPORT",
            user_id=str(vendor_id),
            resource_type="vendor",
            resource_id=str(vendor_id),
            is_sensitive=True,
            changes_summary="Data export requested by user",
        )

        logger.info(f"Data export generated for vendor {vendor_id}")

        # Return as downloadable JSON
        return JSONResponse(
            content=data_package,
            headers={
                "Content-Disposition": f"attachment; filename=marketprep_data_export_{datetime.utcnow().strftime('%Y%m%d')}.json",
            },
        )

    except Exception as e:
        logger.error(f"Error exporting vendor data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate data export",
        )


@router.delete("/me")
async def delete_vendor_account(
    delete_request: DeleteAccountRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete vendor account (GDPR Article 17 - Right to erasure)

    Permanently deletes all vendor data or anonymizes it based on
    retention requirements.

    Args:
        delete_request: Deletion confirmation
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        Deletion confirmation
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    # Verify email confirmation
    if delete_request.confirm_email != vendor.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email confirmation does not match",
        )

    gdpr_service = GDPRService(db)

    try:
        # Create DSAR for deletion
        from src.models.gdpr_compliance import DSARType

        dsar = gdpr_service.create_dsar(
            vendor_id=str(vendor_id),
            user_id=str(vendor_id),
            user_email=vendor.email,
            request_type=DSARType.ERASURE,
            description=delete_request.reason or "User requested account deletion",
        )

        # Perform deletion (anonymize instead of hard delete for compliance)
        deletion_counts = gdpr_service.delete_user_data(
            user_id=str(vendor_id),
            dsar_id=dsar.id,
            anonymize=True,  # Anonymize to preserve audit trails
        )

        # Mark DSAR as completed
        from src.models.gdpr_compliance import DSARStatus
        dsar.status = DSARStatus.COMPLETED
        dsar.completed_at = datetime.utcnow()
        dsar.completion_notes = f"Account anonymized: {deletion_counts}"
        db.commit()

        logger.info(f"Vendor account deleted/anonymized: {vendor_id}")

        return {
            "message": "Account deletion completed",
            "dsar_id": str(dsar.id),
            "anonymized": True,
            "deletion_counts": deletion_counts,
        }

    except ValueError as e:
        # Legal hold or other constraint
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting vendor account: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )


@router.get("/me/data-requests")
def get_vendor_data_requests(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> list:
    """
    Get vendor's data subject access requests (DSARs)

    Args:
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        List of DSARs
    """
    from src.models.gdpr_compliance import DataSubjectRequest

    requests = (
        db.query(DataSubjectRequest)
        .filter(DataSubjectRequest.user_id == vendor_id)
        .order_by(DataSubjectRequest.requested_at.desc())
        .all()
    )

    return [
        {
            "id": str(req.id),
            "request_type": req.request_type,
            "status": req.status,
            "requested_at": req.requested_at.isoformat(),
            "deadline": req.deadline.isoformat(),
            "completed_at": req.completed_at.isoformat() if req.completed_at else None,
            "description": req.description,
        }
        for req in requests
    ]


@router.get("/me/consents")
def get_vendor_consents(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> list:
    """
    Get vendor's consent history

    Args:
        vendor_id: Current vendor UUID
        db: Database session

    Returns:
        List of consents
    """
    from src.models.gdpr_compliance import UserConsent

    consents = (
        db.query(UserConsent)
        .filter(UserConsent.user_id == vendor_id)
        .order_by(UserConsent.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(consent.id),
            "consent_type": consent.consent_type,
            "consent_given": consent.consent_given,
            "given_at": consent.given_at.isoformat() if consent.given_at else None,
            "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
            "consent_version": consent.consent_version,
        }
        for consent in consents
    ]
