"""
Unit tests for audit log service

Tests audit logging functionality:
- Log action recording
- Data access logging
- Hash chain generation
- Audit trail queries
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.audit_service import AuditService
from src.models.audit_log import AuditLog, AuditAction


class TestAuditLogCreation:
    """Test audit log creation"""

    def test_log_action(self, db):
        """Test basic action logging"""
        service = AuditService(db)

        log = service.log_action(
            vendor_id="vendor-123",
            action=AuditAction.CREATE,
            user_email="user@example.com",
            resource_type="product",
            resource_id="prod-123",
            changes_summary="Created new product"
        )

        assert log.id is not None
        assert log.vendor_id == "vendor-123"
        assert log.action == AuditAction.CREATE
        assert log.resource_type == "product"

    def test_log_action_with_old_new_values(self, db):
        """Test logging with before/after values"""
        service = AuditService(db)

        old_values = {"name": "Old Name", "price": 10.0}
        new_values = {"name": "New Name", "price": 12.0}

        log = service.log_action(
            vendor_id="vendor-123",
            action=AuditAction.UPDATE,
            resource_type="product",
            resource_id="prod-123",
            old_values=old_values,
            new_values=new_values
        )

        assert log.old_values == old_values
        assert log.new_values == new_values


class TestDataAccessLogging:
    """Test GDPR data access logging"""

    def test_log_data_access(self, db):
        """Test data access logging"""
        service = AuditService(db)

        access_log = service.log_data_access(
            vendor_id="vendor-123",
            accessor_id="admin-1",
            accessor_email="admin@example.com",
            accessor_role="admin",
            data_subject_id="vendor-123",
            data_subject_email="vendor@example.com",
            data_type="sales_data",
            access_method="export",
            access_purpose="GDPR data export request",
            legal_basis="consent"
        )

        assert access_log.id is not None
        assert access_log.data_type == "sales_data"
        assert access_log.legal_basis == "consent"


# Additional unit tests for:
# - Audit trail retrieval
# - Filtering by date range
# - Sensitive data flagging
# - IP address and user agent capture
# - Correlation ID linking
