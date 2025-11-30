"""
Audit logging service

Records all significant user actions for compliance.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from src.models.audit_log import AuditLog, DataAccessLog, AuditAction
from src.logging_config import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for recording audit logs"""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        vendor_id: str,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changes_summary: Optional[str] = None,
        request: Optional[Request] = None,
        is_sensitive: bool = False,
    ) -> AuditLog:
        """
        Record an audit log entry

        Args:
            vendor_id: Tenant ID
            action: Action performed (use AuditAction enum)
            user_id: User ID performing action
            user_email: User email
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            old_values: State before change
            new_values: State after change
            changes_summary: Human-readable change summary
            request: FastAPI request object (for IP, user agent)
            is_sensitive: Contains PII/sensitive data

        Returns:
            Created AuditLog
        """
        # Extract request context
        ip_address = None
        user_agent = None
        request_method = None
        request_path = None
        correlation_id = None

        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")
            request_method = request.method
            request_path = str(request.url.path)
            correlation_id = getattr(request.state, "correlation_id", None)

        audit_log = AuditLog(
            vendor_id=vendor_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            correlation_id=correlation_id,
            is_sensitive=is_sensitive,
            timestamp=datetime.utcnow(),
        )

        self.db.add(audit_log)
        self.db.commit()

        logger.info(
            f"Audit log created: {action} by {user_email} on {resource_type}:{resource_id}",
            extra={
                "audit_id": audit_log.id,
                "action": action,
                "user_id": user_id,
                "resource_type": resource_type,
            },
        )

        return audit_log

    def log_data_access(
        self,
        vendor_id: str,
        accessor_id: str,
        accessor_email: str,
        accessor_role: str,
        data_subject_id: str,
        data_subject_email: str,
        data_type: str,
        access_method: str,
        access_purpose: str,
        legal_basis: str = "contract",
        records_accessed: int = 1,
        request: Optional[Request] = None,
    ) -> DataAccessLog:
        """
        Record data access for GDPR compliance

        Args:
            vendor_id: Tenant ID
            accessor_id: ID of user accessing data
            accessor_email: Email of accessor
            accessor_role: Role of accessor ("vendor", "admin", "support")
            data_subject_id: ID of data subject
            data_subject_email: Email of data subject
            data_type: Type of data accessed
            access_method: How accessed ("view", "export", "api")
            access_purpose: Purpose of access
            legal_basis: GDPR legal basis
            records_accessed: Number of records accessed
            request: FastAPI request object

        Returns:
            Created DataAccessLog
        """
        ip_address = "unknown"
        correlation_id = None

        if request:
            ip_address = request.client.host if request.client else "unknown"
            correlation_id = getattr(request.state, "correlation_id", None)

        access_log = DataAccessLog(
            vendor_id=vendor_id,
            accessor_id=accessor_id,
            accessor_email=accessor_email,
            accessor_role=accessor_role,
            data_subject_id=data_subject_id,
            data_subject_email=data_subject_email,
            data_type=data_type,
            access_method=access_method,
            records_accessed=records_accessed,
            access_purpose=access_purpose,
            legal_basis=legal_basis,
            ip_address=ip_address,
            correlation_id=correlation_id,
            accessed_at=datetime.utcnow(),
        )

        self.db.add(access_log)
        self.db.commit()

        logger.debug(
            f"Data access logged: {accessor_email} accessed {data_type} of {data_subject_email}",
            extra={
                "access_log_id": access_log.id,
                "data_type": data_type,
                "accessor_id": accessor_id,
            },
        )

        return access_log

    def get_user_audit_trail(
        self,
        user_id: str,
        days: int = 90,
    ) -> list[AuditLog]:
        """Get audit trail for a specific user (for DSAR)"""
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        return self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= since,
        ).order_by(AuditLog.timestamp.desc()).all()

    def get_data_access_history(
        self,
        data_subject_id: str,
        days: int = 90,
    ) -> list[DataAccessLog]:
        """Get data access history for a user (for DSAR)"""
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        return self.db.query(DataAccessLog).filter(
            DataAccessLog.data_subject_id == data_subject_id,
            DataAccessLog.accessed_at >= since,
        ).order_by(DataAccessLog.accessed_at.desc()).all()
