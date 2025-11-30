"""
Audit logging models for compliance

Tracks all user actions and data access for compliance requirements.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import TenantModel


class AuditAction(str, Enum):
    """Audit action types"""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # Data access
    VIEW = "view"
    EXPORT = "export"
    SEARCH = "search"

    # Data modification
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # Subscription & billing
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"

    # GDPR actions
    DATA_EXPORT_REQUESTED = "data_export_requested"
    DATA_DELETION_REQUESTED = "data_deletion_requested"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"

    # Admin actions
    USER_IMPERSONATED = "user_impersonated"
    PERMISSION_CHANGED = "permission_changed"
    SETTING_CHANGED = "setting_changed"


class AuditLog(TenantModel):
    """
    Comprehensive audit log for compliance

    Tracks all significant user actions and data access.
    Immutable - records are never updated, only created.
    """
    __tablename__ = "audit_logs"

    # User information
    user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    impersonator_id: Mapped[Optional[str]] = mapped_column(String(36))  # If admin impersonating

    # Action details
    action: Mapped[str] = mapped_column(String(50), index=True)  # AuditAction enum
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # "product", "recommendation", etc.
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Change details
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)  # Before state
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)  # After state
    changes_summary: Mapped[Optional[str]] = mapped_column(Text)  # Human-readable summary

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    request_method: Mapped[Optional[str]] = mapped_column(String(10))  # GET, POST, etc.
    request_path: Mapped[Optional[str]] = mapped_column(String(500))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Compliance flags
    is_sensitive: Mapped[bool] = mapped_column(default=False, index=True)  # Contains PII
    retention_required: Mapped[bool] = mapped_column(default=True)  # Must retain for compliance

    # Timestamp (immutable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
    )

    # Indexes for fast querying
    __table_args__ = (
        Index('ix_audit_vendor_action_timestamp', 'vendor_id', 'action', 'timestamp'),
        Index('ix_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_timestamp_sensitive', 'timestamp', 'is_sensitive'),
        TenantModel.__table_args__,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"user={self.user_email}, timestamp={self.timestamp})>"
        )


class DataAccessLog(TenantModel):
    """
    Specific tracking for data access (GDPR Article 15)

    Records who accessed what data and when.
    Required for data subject access requests (DSAR).
    """
    __tablename__ = "data_access_logs"

    # User accessing data
    accessor_id: Mapped[str] = mapped_column(String(36), index=True)
    accessor_email: Mapped[str] = mapped_column(String(255))
    accessor_role: Mapped[str] = mapped_column(String(50))  # "vendor", "admin", "support"

    # Data subject (whose data was accessed)
    data_subject_id: Mapped[str] = mapped_column(String(36), index=True)
    data_subject_email: Mapped[str] = mapped_column(String(255))

    # Access details
    data_type: Mapped[str] = mapped_column(String(50), index=True)  # "profile", "sales", "recommendations"
    access_method: Mapped[str] = mapped_column(String(20))  # "view", "export", "api"
    records_accessed: Mapped[int] = mapped_column(default=1)  # Number of records

    # Purpose (GDPR requires purpose of processing)
    access_purpose: Mapped[str] = mapped_column(String(200))  # "customer_support", "analytics", etc.
    legal_basis: Mapped[str] = mapped_column(String(50))  # "consent", "contract", "legitimate_interest"

    # Request context
    ip_address: Mapped[str] = mapped_column(String(45))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Timestamp
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
    )

    # Indexes
    __table_args__ = (
        Index('ix_data_access_subject_time', 'data_subject_id', 'accessed_at'),
        Index('ix_data_access_accessor_time', 'accessor_id', 'accessed_at'),
        Index('ix_data_access_vendor_type', 'vendor_id', 'data_type'),
        TenantModel.__table_args__,
    )
