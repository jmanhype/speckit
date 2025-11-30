"""
Data retention policy service

Manages configurable data retention policies per tenant.
Handles automated data archival and deletion based on policy rules.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.gdpr_compliance import DataRetentionPolicy, LegalHold, DataDeletionLog
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.audit_log import AuditLog
from src.logging_config import get_logger

logger = get_logger(__name__)


class RetentionPolicyService:
    """Service for managing and enforcing data retention policies"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Policy Management
    # ========================================================================

    def create_policy(
        self,
        vendor_id: str,
        data_type: str,
        retention_days: int,
        legal_basis: str,
        description: str,
        auto_delete_enabled: bool = True,
        anonymize_instead: bool = False,
    ) -> DataRetentionPolicy:
        """
        Create a new retention policy

        Args:
            vendor_id: Tenant ID
            data_type: Type of data (sales, recommendations, audit_logs, etc.)
            retention_days: Number of days to retain data
            legal_basis: Legal reason for retention
            description: Human-readable description
            auto_delete_enabled: Whether to automatically enforce policy
            anonymize_instead: Anonymize instead of delete

        Returns:
            Created policy
        """
        policy = DataRetentionPolicy(
            vendor_id=vendor_id,
            data_type=data_type,
            retention_days=retention_days,
            legal_basis=legal_basis,
            description=description,
            auto_delete_enabled=auto_delete_enabled,
            anonymize_instead=anonymize_instead,
            is_active=True,
            effective_date=datetime.utcnow(),
        )

        self.db.add(policy)
        self.db.commit()

        logger.info(
            f"Retention policy created: {data_type} = {retention_days} days for vendor {vendor_id}"
        )
        return policy

    def get_policy(self, vendor_id: str, data_type: str) -> Optional[DataRetentionPolicy]:
        """Get active retention policy for data type"""
        return self.db.query(DataRetentionPolicy).filter(
            and_(
                DataRetentionPolicy.vendor_id == vendor_id,
                DataRetentionPolicy.data_type == data_type,
                DataRetentionPolicy.is_active == True,
            )
        ).first()

    def list_policies(self, vendor_id: str, active_only: bool = True) -> List[DataRetentionPolicy]:
        """List all retention policies for vendor"""
        query = self.db.query(DataRetentionPolicy).filter(
            DataRetentionPolicy.vendor_id == vendor_id
        )

        if active_only:
            query = query.filter(DataRetentionPolicy.is_active == True)

        return query.all()

    def update_policy(
        self,
        policy_id: str,
        retention_days: Optional[int] = None,
        auto_delete_enabled: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> DataRetentionPolicy:
        """Update existing retention policy"""
        policy = self.db.query(DataRetentionPolicy).filter(
            DataRetentionPolicy.id == policy_id
        ).first()

        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")

        if retention_days is not None:
            policy.retention_days = retention_days

        if auto_delete_enabled is not None:
            policy.auto_delete_enabled = auto_delete_enabled

        if is_active is not None:
            policy.is_active = is_active

        self.db.commit()

        logger.info(f"Retention policy updated: {policy_id}")
        return policy

    def delete_policy(self, policy_id: str) -> None:
        """Deactivate retention policy (soft delete)"""
        policy = self.db.query(DataRetentionPolicy).filter(
            DataRetentionPolicy.id == policy_id
        ).first()

        if policy:
            policy.is_active = False
            self.db.commit()
            logger.info(f"Retention policy deactivated: {policy_id}")

    # ========================================================================
    # Policy Enforcement
    # ========================================================================

    def enforce_policy(
        self,
        policy: DataRetentionPolicy,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Enforce a single retention policy

        Args:
            policy: Policy to enforce
            dry_run: If True, only count records without deleting

        Returns:
            Dictionary with deletion/anonymization counts
        """
        # Check for legal holds
        if self._has_legal_hold(policy):
            logger.info(f"Skipping policy {policy.id}: active legal hold")
            return {"skipped": 1, "reason": "legal_hold"}

        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

        # Route to appropriate handler based on data type
        if policy.data_type == "sales":
            return self._enforce_sales_policy(policy, cutoff_date, dry_run)
        elif policy.data_type == "recommendations":
            return self._enforce_recommendations_policy(policy, cutoff_date, dry_run)
        elif policy.data_type == "audit_logs":
            return self._enforce_audit_logs_policy(policy, cutoff_date, dry_run)
        else:
            logger.warning(f"Unknown data type: {policy.data_type}")
            return {"error": "unknown_data_type"}

    def enforce_all_policies(
        self,
        vendor_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Enforce all active retention policies

        Args:
            vendor_id: If provided, only enforce for this vendor
            dry_run: If True, only count without deleting

        Returns:
            Summary of enforcement results
        """
        query = self.db.query(DataRetentionPolicy).filter(
            and_(
                DataRetentionPolicy.is_active == True,
                DataRetentionPolicy.auto_delete_enabled == True,
            )
        )

        if vendor_id:
            query = query.filter(DataRetentionPolicy.vendor_id == vendor_id)

        policies = query.all()

        results = {
            "total_policies": len(policies),
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat(),
            "policies": [],
        }

        for policy in policies:
            try:
                counts = self.enforce_policy(policy, dry_run)
                results["policies"].append({
                    "policy_id": policy.id,
                    "vendor_id": policy.vendor_id,
                    "data_type": policy.data_type,
                    "retention_days": policy.retention_days,
                    "counts": counts,
                })
            except Exception as e:
                logger.error(f"Error enforcing policy {policy.id}: {e}", exc_info=True)
                results["policies"].append({
                    "policy_id": policy.id,
                    "error": str(e),
                })

        logger.info(f"Retention enforcement complete: {len(policies)} policies processed")
        return results

    # ========================================================================
    # Data Type Handlers
    # ========================================================================

    def _enforce_sales_policy(
        self,
        policy: DataRetentionPolicy,
        cutoff_date: datetime,
        dry_run: bool,
    ) -> Dict[str, int]:
        """Enforce retention policy for sales data"""
        old_sales = self.db.query(Sale).filter(
            and_(
                Sale.vendor_id == policy.vendor_id,
                Sale.sale_date < cutoff_date,
            )
        ).all()

        count = len(old_sales)

        if dry_run:
            return {"sales": count, "dry_run": True}

        for sale in old_sales:
            if policy.anonymize_instead:
                # Anonymize instead of delete
                sale.vendor_id = "anonymized"
                self._log_deletion(
                    policy.vendor_id,
                    "sale",
                    sale.id,
                    {"quantity": sale.quantity},
                    None,
                    anonymized=True,
                )
            else:
                # Hard delete
                self._log_deletion(
                    policy.vendor_id,
                    "sale",
                    sale.id,
                    {"quantity": sale.quantity, "amount": float(sale.total_amount) if sale.total_amount else None},
                    None,
                )
                self.db.delete(sale)

        self.db.commit()

        logger.info(
            f"Sales retention enforced: {count} records {'anonymized' if policy.anonymize_instead else 'deleted'}"
        )
        return {"sales": count, "anonymized": policy.anonymize_instead}

    def _enforce_recommendations_policy(
        self,
        policy: DataRetentionPolicy,
        cutoff_date: datetime,
        dry_run: bool,
    ) -> Dict[str, int]:
        """Enforce retention policy for recommendations"""
        old_recs = self.db.query(Recommendation).filter(
            and_(
                Recommendation.vendor_id == policy.vendor_id,
                Recommendation.market_date < cutoff_date,
            )
        ).all()

        count = len(old_recs)

        if dry_run:
            return {"recommendations": count, "dry_run": True}

        for rec in old_recs:
            self._log_deletion(
                policy.vendor_id,
                "recommendation",
                rec.id,
                {"product_id": rec.product_id},
                None,
            )
            self.db.delete(rec)

        self.db.commit()

        logger.info(f"Recommendations retention enforced: {count} records deleted")
        return {"recommendations": count}

    def _enforce_audit_logs_policy(
        self,
        policy: DataRetentionPolicy,
        cutoff_date: datetime,
        dry_run: bool,
    ) -> Dict[str, int]:
        """Enforce retention policy for audit logs"""
        # Only delete non-sensitive logs that don't require retention
        old_logs = self.db.query(AuditLog).filter(
            and_(
                AuditLog.vendor_id == policy.vendor_id,
                AuditLog.timestamp < cutoff_date,
                AuditLog.is_sensitive == False,
                AuditLog.retention_required == False,
            )
        ).all()

        count = len(old_logs)

        if dry_run:
            return {"audit_logs": count, "dry_run": True}

        for log in old_logs:
            self.db.delete(log)

        self.db.commit()

        logger.info(f"Audit logs retention enforced: {count} records deleted")
        return {"audit_logs": count}

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _has_legal_hold(self, policy: DataRetentionPolicy) -> bool:
        """Check if policy data type has active legal hold"""
        holds = self.db.query(LegalHold).filter(
            and_(
                LegalHold.vendor_id == policy.vendor_id,
                LegalHold.is_active == True,
            )
        ).all()

        for hold in holds:
            if policy.data_type in hold.data_types:
                return True

        return False

    def _log_deletion(
        self,
        vendor_id: str,
        data_type: str,
        record_id: str,
        summary: Dict[str, Any],
        dsar_id: Optional[str],
        anonymized: bool = False,
    ):
        """Log data deletion for audit trail"""
        log = DataDeletionLog(
            vendor_id=vendor_id,
            data_type=data_type,
            record_id=record_id,
            deletion_reason="retention_policy",
            deleted_by="system",
            user_request_id=dsar_id,
            record_summary=summary,
            anonymized=anonymized,
            deleted_at=datetime.utcnow(),
        )
        self.db.add(log)

    def get_deletion_history(
        self,
        vendor_id: str,
        days: int = 90,
    ) -> List[DataDeletionLog]:
        """Get deletion history for vendor"""
        since = datetime.utcnow() - timedelta(days=days)

        return self.db.query(DataDeletionLog).filter(
            and_(
                DataDeletionLog.vendor_id == vendor_id,
                DataDeletionLog.deleted_at >= since,
            )
        ).order_by(DataDeletionLog.deleted_at.desc()).all()

    def get_retention_status(self, vendor_id: str) -> Dict[str, Any]:
        """Get retention policy status for vendor"""
        policies = self.list_policies(vendor_id, active_only=True)

        status = {
            "vendor_id": vendor_id,
            "total_policies": len(policies),
            "policies": [],
        }

        for policy in policies:
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

            # Count affected records
            if policy.data_type == "sales":
                affected_count = self.db.query(Sale).filter(
                    and_(
                        Sale.vendor_id == vendor_id,
                        Sale.sale_date < cutoff_date,
                    )
                ).count()
            elif policy.data_type == "recommendations":
                affected_count = self.db.query(Recommendation).filter(
                    and_(
                        Recommendation.vendor_id == vendor_id,
                        Recommendation.market_date < cutoff_date,
                    )
                ).count()
            else:
                affected_count = 0

            status["policies"].append({
                "data_type": policy.data_type,
                "retention_days": policy.retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "affected_records": affected_count,
                "auto_delete": policy.auto_delete_enabled,
                "anonymize_instead": policy.anonymize_instead,
            })

        return status
