"""
GDPR compliance models

Tracks consent, data subject requests, and data retention.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import TenantModel


class ConsentType(str, Enum):
    """Types of consent required"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    DATA_PROCESSING = "data_processing"
    THIRD_PARTY_SHARING = "third_party_sharing"


class DSARStatus(str, Enum):
    """Data Subject Access Request status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DSARType(str, Enum):
    """Types of DSAR"""
    ACCESS = "access"  # Article 15 - Right to access
    RECTIFICATION = "rectification"  # Article 16 - Right to rectification
    ERASURE = "erasure"  # Article 17 - Right to erasure
    RESTRICTION = "restriction"  # Article 18 - Right to restriction
    PORTABILITY = "portability"  # Article 20 - Right to portability
    OBJECTION = "objection"  # Article 21 - Right to object


class UserConsent(TenantModel):
    """
    User consent tracking (GDPR Article 7)

    Tracks user consent for various data processing activities.
    """
    __tablename__ = "user_consents"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    user_email: Mapped[str] = mapped_column(String(255))

    # Consent details
    consent_type: Mapped[str] = mapped_column(String(50), index=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    consent_text: Mapped[str] = mapped_column(Text)  # Exact text user agreed to

    # Timestamps
    given_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # Optional expiry

    # Context
    ip_address: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))

    # Version tracking (in case consent text changes)
    consent_version: Mapped[str] = mapped_column(String(20), default="1.0")

    __table_args__ = (
        Index('ix_consent_user_type', 'user_id', 'consent_type'),
        Index('ix_consent_vendor_given', 'vendor_id', 'consent_given'),
        TenantModel.__table_args__,
    )


class DataSubjectRequest(TenantModel):
    """
    Data Subject Access Requests (DSAR)

    Tracks GDPR data subject requests.
    Must be fulfilled within 30 days (Article 12).
    """
    __tablename__ = "data_subject_requests"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)

    # Request details
    request_type: Mapped[str] = mapped_column(String(50), index=True)  # DSARType enum
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)

    # Request description
    description: Mapped[Optional[str]] = mapped_column(Text)
    specific_data: Mapped[Optional[str]] = mapped_column(Text)  # Specific data requested

    # Fulfillment
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[Optional[str]] = mapped_column(String(36))  # Admin user ID
    completion_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Export/deletion details
    export_file_url: Mapped[Optional[str]] = mapped_column(String(500))  # For access/portability requests
    deletion_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # For erasure requests

    # Timestamps (30-day deadline tracking)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)  # Must complete by

    __table_args__ = (
        Index('ix_dsar_vendor_status', 'vendor_id', 'status'),
        Index('ix_dsar_deadline', 'deadline'),
        Index('ix_dsar_user_type', 'user_id', 'request_type'),
        TenantModel.__table_args__,
    )


class DataRetentionPolicy(TenantModel):
    """
    Data retention policies (GDPR Article 5)

    Defines how long different types of data should be retained.
    """
    __tablename__ = "data_retention_policies"

    # Policy details
    data_type: Mapped[str] = mapped_column(String(50), index=True)  # "sales", "recommendations", etc.
    description: Mapped[str] = mapped_column(Text)

    # Retention period
    retention_days: Mapped[int]  # How many days to retain
    legal_basis: Mapped[str] = mapped_column(String(100))  # Legal reason for retention

    # Deletion behavior
    auto_delete_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    anonymize_instead: Mapped[bool] = mapped_column(Boolean, default=False)  # Anonymize instead of delete

    # Policy status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index('ix_retention_vendor_type', 'vendor_id', 'data_type'),
        TenantModel.__table_args__,
    )


class LegalHold(TenantModel):
    """
    Legal holds (prevents deletion despite retention policies)

    Used when data must be preserved for legal/compliance reasons.
    """
    __tablename__ = "legal_holds"

    # Hold details
    hold_name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(200))  # "litigation", "investigation", etc.

    # Scope
    data_types: Mapped[list[str]] = mapped_column(JSON)  # List of data types on hold
    user_ids: Mapped[Optional[list[str]]] = mapped_column(JSON)  # Specific users (or null for all)

    # Timestamps
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # When hold is released

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    released_by: Mapped[Optional[str]] = mapped_column(String(36))  # Admin who released hold

    __table_args__ = (
        Index('ix_legal_hold_vendor_active', 'vendor_id', 'is_active'),
        TenantModel.__table_args__,
    )


class DataDeletionLog(TenantModel):
    """
    Log of data deletions for compliance audit

    Tracks when data was deleted and why.
    """
    __tablename__ = "data_deletion_logs"

    # Deletion details
    data_type: Mapped[str] = mapped_column(String(50), index=True)
    record_id: Mapped[str] = mapped_column(String(36))
    deletion_reason: Mapped[str] = mapped_column(String(100))  # "retention_policy", "user_request", etc.

    # User context
    deleted_by: Mapped[Optional[str]] = mapped_column(String(36))  # User ID (or "system" for automated)
    user_request_id: Mapped[Optional[str]] = mapped_column(String(36))  # Link to DSAR if applicable

    # Record summary (what was deleted)
    record_summary: Mapped[dict] = mapped_column(JSON)  # Summary of deleted data (no PII)

    # Timestamp
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Was data anonymized instead of deleted?
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index('ix_deletion_vendor_type_date', 'vendor_id', 'data_type', 'deleted_at'),
        Index('ix_deletion_reason', 'deletion_reason'),
        TenantModel.__table_args__,
    )
