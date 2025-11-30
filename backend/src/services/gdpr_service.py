"""
GDPR compliance service

Handles data subject requests, consent management, and data portability.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.gdpr_compliance import (
    UserConsent,
    DataSubjectRequest,
    DSARType,
    DSARStatus,
    DataRetentionPolicy,
    LegalHold,
    DataDeletionLog,
)
from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.logging_config import get_logger

logger = get_logger(__name__)


class GDPRService:
    """Service for GDPR compliance operations"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Consent Management (Article 7)
    # ========================================================================

    def record_consent(
        self,
        vendor_id: str,
        user_id: str,
        user_email: str,
        consent_type: str,
        consent_given: bool,
        consent_text: str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> UserConsent:
        """Record user consent"""
        consent = UserConsent(
            vendor_id=vendor_id,
            user_id=user_id,
            user_email=user_email,
            consent_type=consent_type,
            consent_given=consent_given,
            consent_text=consent_text,
            given_at=datetime.utcnow() if consent_given else None,
            withdrawn_at=None if consent_given else datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(consent)
        self.db.commit()

        logger.info(f"Consent recorded: {consent_type} = {consent_given} for {user_email}")
        return consent

    def withdraw_consent(
        self,
        user_id: str,
        consent_type: str,
    ) -> UserConsent:
        """Withdraw previously given consent"""
        consent = self.db.query(UserConsent).filter(
            and_(
                UserConsent.user_id == user_id,
                UserConsent.consent_type == consent_type,
                UserConsent.consent_given == True,
            )
        ).first()

        if consent:
            consent.consent_given = False
            consent.withdrawn_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Consent withdrawn: {consent_type} for user {user_id}")

        return consent

    # ========================================================================
    # Data Subject Access Requests (DSAR)
    # ========================================================================

    def create_dsar(
        self,
        vendor_id: str,
        user_id: str,
        user_email: str,
        request_type: str,
        description: Optional[str] = None,
    ) -> DataSubjectRequest:
        """
        Create a data subject access request

        Must be fulfilled within 30 days per GDPR Article 12.
        """
        deadline = datetime.utcnow() + timedelta(days=30)

        dsar = DataSubjectRequest(
            vendor_id=vendor_id,
            user_id=user_id,
            user_email=user_email,
            request_type=request_type,
            status=DSARStatus.PENDING,
            description=description,
            requested_at=datetime.utcnow(),
            deadline=deadline,
        )

        self.db.add(dsar)
        self.db.commit()

        logger.info(f"DSAR created: {request_type} for {user_email}, deadline {deadline}")
        return dsar

    def export_user_data(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Export all user data (Article 15 - Right to access)

        Returns complete data package in machine-readable format.
        """
        from src.models.vendor import Vendor

        # Gather all user data
        vendor = self.db.query(Vendor).filter(Vendor.id == user_id).first()

        data_package = {
            "export_date": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "personal_information": {
                "email": vendor.email if vendor else None,
                "name": vendor.business_name if vendor else None,
                "created_at": vendor.created_at.isoformat() if vendor and vendor.created_at else None,
            },
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": float(p.price) if p.price else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in self.db.query(Product).filter(Product.vendor_id == user_id).all()
            ],
            "sales": [
                {
                    "id": s.id,
                    "product_id": s.product_id,
                    "quantity": s.quantity,
                    "total_amount": float(s.total_amount) if s.total_amount else None,
                    "sale_date": s.sale_date.isoformat() if s.sale_date else None,
                }
                for s in self.db.query(Sale).filter(Sale.vendor_id == user_id).all()
            ],
            "recommendations": [
                {
                    "id": r.id,
                    "product_id": r.product_id,
                    "market_date": r.market_date.isoformat() if r.market_date else None,
                    "recommended_quantity": r.recommended_quantity,
                    "confidence_score": float(r.confidence_score) if r.confidence_score else None,
                }
                for r in self.db.query(Recommendation).filter(Recommendation.vendor_id == user_id).all()
            ],
            "feedback": [
                {
                    "id": f.id,
                    "recommendation_id": f.recommendation_id,
                    "actual_quantity_sold": f.actual_quantity_sold,
                    "rating": f.rating,
                    "was_accurate": f.was_accurate,
                }
                for f in self.db.query(RecommendationFeedback).filter(RecommendationFeedback.vendor_id == user_id).all()
            ],
            "consents": [
                {
                    "consent_type": c.consent_type,
                    "consent_given": c.consent_given,
                    "given_at": c.given_at.isoformat() if c.given_at else None,
                    "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                }
                for c in self.db.query(UserConsent).filter(UserConsent.user_id == user_id).all()
            ],
        }

        logger.info(f"Data export generated for user {user_id}")
        return data_package

    def delete_user_data(
        self,
        user_id: str,
        dsar_id: Optional[str] = None,
        anonymize: bool = False,
    ) -> Dict[str, int]:
        """
        Delete or anonymize user data (Article 17 - Right to erasure)

        Args:
            user_id: User ID
            dsar_id: Related DSAR ID
            anonymize: If True, anonymize instead of delete

        Returns:
            Dictionary with deletion counts by data type
        """
        # Check for legal holds
        active_holds = self.db.query(LegalHold).filter(
            and_(
                LegalHold.vendor_id == user_id,
                LegalHold.is_active == True,
            )
        ).all()

        if active_holds:
            raise ValueError(f"Cannot delete data: {len(active_holds)} active legal hold(s)")

        deletion_counts = {}

        # Delete or anonymize data by type
        if anonymize:
            deletion_counts = self._anonymize_user_data(user_id, dsar_id)
        else:
            deletion_counts = self._delete_user_data(user_id, dsar_id)

        logger.info(f"User data {'anonymized' if anonymize else 'deleted'} for {user_id}: {deletion_counts}")
        return deletion_counts

    def _delete_user_data(self, user_id: str, dsar_id: Optional[str]) -> Dict[str, int]:
        """Actually delete user data"""
        counts = {}

        # Delete products
        products = self.db.query(Product).filter(Product.vendor_id == user_id).all()
        for product in products:
            self._log_deletion(user_id, "product", product.id, {"name": product.name}, dsar_id)
        counts["products"] = len(products)
        self.db.query(Product).filter(Product.vendor_id == user_id).delete()

        # Delete sales
        sales = self.db.query(Sale).filter(Sale.vendor_id == user_id).all()
        counts["sales"] = len(sales)
        for sale in sales:
            self._log_deletion(user_id, "sale", sale.id, {"quantity": sale.quantity}, dsar_id)
        self.db.query(Sale).filter(Sale.vendor_id == user_id).delete()

        # Delete recommendations
        recommendations = self.db.query(Recommendation).filter(Recommendation.vendor_id == user_id).all()
        counts["recommendations"] = len(recommendations)
        for rec in recommendations:
            self._log_deletion(user_id, "recommendation", rec.id, {}, dsar_id)
        self.db.query(Recommendation).filter(Recommendation.vendor_id == user_id).delete()

        self.db.commit()
        return counts

    def _anonymize_user_data(self, user_id: str, dsar_id: Optional[str]) -> Dict[str, int]:
        """Anonymize user data instead of deleting"""
        from src.models.vendor import Vendor

        counts = {}

        # Anonymize vendor profile
        vendor = self.db.query(Vendor).filter(Vendor.id == user_id).first()
        if vendor:
            vendor.email = f"deleted_{hashlib.md5(user_id.encode(), usedforsecurity=False).hexdigest()}@anonymized.local"
            vendor.business_name = f"Deleted User {user_id[:8]}"
            counts["vendor"] = 1
            self._log_deletion(user_id, "vendor", vendor.id, {}, dsar_id, anonymized=True)

        # Keep sales/recommendations but anonymize linkage
        # (Implementation depends on business requirements)

        self.db.commit()
        return counts

    def _log_deletion(
        self,
        vendor_id: str,
        data_type: str,
        record_id: str,
        summary: Dict[str, Any],
        dsar_id: Optional[str],
        anonymized: bool = False,
    ):
        """Log data deletion for audit"""
        log = DataDeletionLog(
            vendor_id=vendor_id,
            data_type=data_type,
            record_id=record_id,
            deletion_reason="user_request" if dsar_id else "retention_policy",
            deleted_by=vendor_id,
            user_request_id=dsar_id,
            record_summary=summary,
            anonymized=anonymized,
            deleted_at=datetime.utcnow(),
        )
        self.db.add(log)

    # ========================================================================
    # Retention Policies
    # ========================================================================

    def apply_retention_policies(self) -> Dict[str, int]:
        """
        Apply data retention policies (automated cleanup)

        Returns counts of records processed by data type.
        """
        policies = self.db.query(DataRetentionPolicy).filter(
            and_(
                DataRetentionPolicy.is_active == True,
                DataRetentionPolicy.auto_delete_enabled == True,
            )
        ).all()

        deletion_counts = {}

        for policy in policies:
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

            # Check for legal holds
            active_holds = self.db.query(LegalHold).filter(
                and_(
                    LegalHold.is_active == True,
                    LegalHold.data_types.contains([policy.data_type]),
                )
            ).first()

            if active_holds:
                logger.info(f"Skipping retention for {policy.data_type}: active legal hold")
                continue

            # Apply policy based on data type
            if policy.data_type == "sales":
                old_sales = self.db.query(Sale).filter(Sale.sale_date < cutoff_date).all()
                for sale in old_sales:
                    if policy.anonymize_instead:
                        # Anonymize instead of delete
                        sale.vendor_id = "anonymized"
                    else:
                        self._log_deletion(sale.vendor_id, "sale", sale.id, {}, None)
                        self.db.delete(sale)
                deletion_counts["sales"] = len(old_sales)

            # Add more data types as needed

        self.db.commit()
        logger.info(f"Retention policies applied: {deletion_counts}")
        return deletion_counts
