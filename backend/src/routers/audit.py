"""Audit log verification API routes.

Endpoints:
- GET /audit/verify - Verify hash chain integrity
- GET /audit/logs - List audit logs (admin only)
- GET /audit/access-logs - List data access logs (admin only)
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.audit_log import AuditLog, DataAccessLog
from src.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


class HashChainVerificationResponse(BaseModel):
    """Hash chain verification result."""

    is_valid: bool
    total_logs_checked: int
    first_log_timestamp: Optional[str]
    last_log_timestamp: Optional[str]
    broken_chain_at: Optional[str] = None
    broken_log_id: Optional[UUID] = None
    message: str


class AuditLogResponse(BaseModel):
    """Audit log response."""

    id: UUID
    vendor_id: str
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    changes_summary: Optional[str]
    ip_address: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    timestamp: str
    is_sensitive: bool

    class Config:
        from_attributes = True


class DataAccessLogResponse(BaseModel):
    """Data access log response."""

    id: UUID
    vendor_id: str
    accessor_email: str
    accessor_role: str
    data_subject_email: str
    data_type: str
    access_method: str
    access_purpose: str
    legal_basis: str
    records_accessed: int
    accessed_at: str

    class Config:
        from_attributes = True


@router.get("/verify", response_model=HashChainVerificationResponse)
def verify_hash_chain(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days_back: int = Query(90, ge=1, le=365, description="Days of logs to verify"),
) -> HashChainVerificationResponse:
    """Verify hash chain integrity of audit logs.

    Validates that audit logs have not been tampered with by verifying
    the cryptographic hash chain.

    Args:
        vendor_id: Current vendor ID (from auth)
        db: Database session
        days_back: Number of days of logs to verify

    Returns:
        Verification result with details

    Example Response:
        {
            "is_valid": true,
            "total_logs_checked": 1523,
            "first_log_timestamp": "2024-01-01T00:00:00Z",
            "last_log_timestamp": "2024-03-31T23:59:59Z",
            "message": "Hash chain is valid. All 1523 logs verified."
        }
    """
    # Calculate date range
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    # Get all audit logs for vendor in time range, ordered by timestamp
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.vendor_id == str(vendor_id),
            AuditLog.timestamp >= cutoff_date,
        )
        .order_by(AuditLog.timestamp.asc())
        .all()
    )

    if not logs:
        return HashChainVerificationResponse(
            is_valid=True,
            total_logs_checked=0,
            first_log_timestamp=None,
            last_log_timestamp=None,
            message="No audit logs found in the specified time range.",
        )

    # Verify hash chain
    is_valid = True
    broken_at = None
    broken_log_id = None

    for i, log in enumerate(logs):
        # First log should have no previous hash
        if i == 0:
            if log.previous_hash is not None and log.previous_hash != "":
                is_valid = False
                broken_at = log.timestamp.isoformat()
                broken_log_id = log.id
                break
            continue

        # Subsequent logs should link to previous
        expected_prev_hash = logs[i - 1].hash_value
        if log.previous_hash != expected_prev_hash:
            is_valid = False
            broken_at = log.timestamp.isoformat()
            broken_log_id = log.id
            break

        # Verify hash matches content
        if not log.verify_hash():
            is_valid = False
            broken_at = log.timestamp.isoformat()
            broken_log_id = log.id
            break

    # Build response
    if is_valid:
        message = f"Hash chain is valid. All {len(logs)} logs verified successfully."
    else:
        message = (
            f"Hash chain is INVALID. Tampering detected at log {broken_log_id} "
            f"on {broken_at}. Possible data integrity breach."
        )

    return HashChainVerificationResponse(
        is_valid=is_valid,
        total_logs_checked=len(logs),
        first_log_timestamp=logs[0].timestamp.isoformat() if logs else None,
        last_log_timestamp=logs[-1].timestamp.isoformat() if logs else None,
        broken_chain_at=broken_at,
        broken_log_id=broken_log_id,
        message=message,
    )


@router.get("/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days_back: int = Query(30, ge=1, le=365),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
) -> List[AuditLogResponse]:
    """List audit logs for current vendor.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        limit: Maximum number of logs
        offset: Offset for pagination
        days_back: Number of days to include
        action: Filter by action
        resource_type: Filter by resource type

    Returns:
        List of audit logs
    """
    # Calculate date range
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    # Build query
    query = db.query(AuditLog).filter(
        AuditLog.vendor_id == str(vendor_id),
        AuditLog.timestamp >= cutoff_date,
    )

    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    # Execute query
    logs = (
        query.order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        AuditLogResponse(
            id=log.id,
            vendor_id=log.vendor_id,
            user_email=log.user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            changes_summary=log.changes_summary,
            ip_address=log.ip_address,
            request_method=log.request_method,
            request_path=log.request_path,
            timestamp=log.timestamp.isoformat(),
            is_sensitive=log.is_sensitive,
        )
        for log in logs
    ]


@router.get("/access-logs", response_model=List[DataAccessLogResponse])
def list_data_access_logs(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days_back: int = Query(30, ge=1, le=365),
) -> List[DataAccessLogResponse]:
    """List data access logs for current vendor.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        limit: Maximum number of logs
        offset: Offset for pagination
        days_back: Number of days to include

    Returns:
        List of data access logs
    """
    # Calculate date range
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    # Query data access logs
    logs = (
        db.query(DataAccessLog)
        .filter(
            DataAccessLog.vendor_id == str(vendor_id),
            DataAccessLog.accessed_at >= cutoff_date,
        )
        .order_by(DataAccessLog.accessed_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        DataAccessLogResponse(
            id=log.id,
            vendor_id=log.vendor_id,
            accessor_email=log.accessor_email,
            accessor_role=log.accessor_role,
            data_subject_email=log.data_subject_email,
            data_type=log.data_type,
            access_method=log.access_method,
            access_purpose=log.access_purpose,
            legal_basis=log.legal_basis,
            records_accessed=log.records_accessed,
            accessed_at=log.accessed_at.isoformat(),
        )
        for log in logs
    ]
