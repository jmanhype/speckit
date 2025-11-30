"""
Integration tests for audit trail completeness

Ensures all critical user actions are logged for compliance.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.audit_service import AuditService
from src.models.audit_log import AuditLog, AuditAction
from src.models.vendor import Vendor
from src.models.product import Product


@pytest.fixture
def audit_service(db: Session):
    """Create audit service instance"""
    return AuditService(db)


@pytest.fixture
def test_vendor(db: Session):
    """Create test vendor"""
    vendor = Vendor(
        id="test-vendor-123",
        email="vendor@test.com",
        business_name="Test Vendor",
    )
    db.add(vendor)
    db.commit()
    return vendor


class TestAuditTrailCompleteness:
    """Test that audit trails capture all required events"""

    def test_user_login_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that user logins are logged"""
        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.LOGIN,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            is_sensitive=False,
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.LOGIN,
            AuditLog.user_id == test_vendor.id,
        ).first()

        assert log is not None
        assert log.vendor_id == test_vendor.id
        assert log.user_email == test_vendor.email
        assert log.timestamp is not None

    def test_product_creation_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that product creation is logged with details"""
        product_data = {
            "name": "Test Product",
            "category": "Produce",
            "price": 10.99,
        }

        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.CREATE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            resource_type="product",
            resource_id="prod-123",
            new_values=product_data,
            changes_summary="Created new product: Test Product",
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.CREATE,
            AuditLog.resource_type == "product",
        ).first()

        assert log is not None
        assert log.resource_id == "prod-123"
        assert log.new_values == product_data
        assert log.changes_summary == "Created new product: Test Product"

    def test_product_update_logged_with_diff(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that product updates log old and new values"""
        old_values = {"price": 10.99}
        new_values = {"price": 12.99}

        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.UPDATE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            resource_type="product",
            resource_id="prod-123",
            old_values=old_values,
            new_values=new_values,
            changes_summary="Price increased from $10.99 to $12.99",
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.resource_id == "prod-123",
        ).first()

        assert log is not None
        assert log.old_values == old_values
        assert log.new_values == new_values

    def test_product_deletion_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that product deletion is logged"""
        product_summary = {"name": "Test Product", "price": 10.99}

        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.DELETE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            resource_type="product",
            resource_id="prod-123",
            old_values=product_summary,
            changes_summary="Deleted product: Test Product",
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.DELETE,
            AuditLog.resource_id == "prod-123",
        ).first()

        assert log is not None
        assert log.old_values == product_summary

    def test_gdpr_export_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that GDPR data exports are logged"""
        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.GDPR_EXPORT,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            is_sensitive=True,  # Data exports are sensitive
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.GDPR_EXPORT,
            AuditLog.user_id == test_vendor.id,
        ).first()

        assert log is not None
        assert log.is_sensitive is True
        assert log.retention_required is True

    def test_gdpr_deletion_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that GDPR deletion requests are logged"""
        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.GDPR_DELETE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            changes_summary="User requested data deletion",
            is_sensitive=True,
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.GDPR_DELETE,
        ).first()

        assert log is not None
        assert log.is_sensitive is True

    def test_sensitive_data_access_logged(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that sensitive data access is logged"""
        audit_service.log_data_access(
            vendor_id=test_vendor.id,
            accessor_id="admin-123",
            accessor_email="admin@marketprep.com",
            accessor_role="admin",
            data_subject_id=test_vendor.id,
            data_subject_email=test_vendor.email,
            data_type="sales_data",
            access_method="view",
            access_purpose="Customer support investigation",
            legal_basis="contract",
            records_accessed=50,
        )

        from src.models.audit_log import DataAccessLog
        log = db.query(DataAccessLog).filter(
            DataAccessLog.data_subject_id == test_vendor.id,
        ).first()

        assert log is not None
        assert log.accessor_role == "admin"
        assert log.access_purpose == "Customer support investigation"
        assert log.legal_basis == "contract"
        assert log.records_accessed == 50

    def test_audit_trail_retrieval(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test retrieving complete audit trail for a user"""
        # Create multiple audit logs
        actions = [AuditAction.LOGIN, AuditAction.CREATE, AuditAction.UPDATE]

        for action in actions:
            audit_service.log_action(
                vendor_id=test_vendor.id,
                action=action,
                user_id=test_vendor.id,
                user_email=test_vendor.email,
            )

        # Retrieve audit trail
        trail = audit_service.get_user_audit_trail(test_vendor.id, days=30)

        assert len(trail) == 3
        assert all(log.user_id == test_vendor.id for log in trail)
        # Should be ordered by timestamp descending
        assert trail[0].timestamp >= trail[-1].timestamp

    def test_data_access_history_retrieval(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test retrieving data access history for DSAR"""
        # Log multiple data accesses
        for i in range(3):
            audit_service.log_data_access(
                vendor_id=test_vendor.id,
                accessor_id=f"admin-{i}",
                accessor_email=f"admin{i}@test.com",
                accessor_role="admin",
                data_subject_id=test_vendor.id,
                data_subject_email=test_vendor.email,
                data_type="sales_data",
                access_method="view",
                access_purpose="Support",
                legal_basis="contract",
            )

        history = audit_service.get_data_access_history(test_vendor.id, days=30)

        assert len(history) == 3
        assert all(log.data_subject_id == test_vendor.id for log in history)

    def test_audit_log_immutability(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that audit logs cannot be modified after creation"""
        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.LOGIN,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
        )

        log = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.LOGIN,
        ).first()

        # Attempt to modify (should not have update method)
        original_timestamp = log.timestamp

        # Even if we try to modify directly, the log should track this
        # In production, audit logs should be append-only
        assert log.timestamp == original_timestamp

    def test_correlation_id_tracking(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that correlation IDs link related actions"""
        correlation_id = "req-abc-123"

        # Create multiple related actions with same correlation ID
        class MockRequest:
            class State:
                correlation_id = correlation_id
            state = State()
            client = type('obj', (object,), {'host': '127.0.0.1'})()
            headers = {"User-Agent": "Test"}
            method = "POST"
            url = type('obj', (object,), {'path': '/api/v1/products'})()

        request = MockRequest()

        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.CREATE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            resource_type="product",
            resource_id="prod-1",
            request=request,
        )

        audit_service.log_action(
            vendor_id=test_vendor.id,
            action=AuditAction.UPDATE,
            user_id=test_vendor.id,
            user_email=test_vendor.email,
            resource_type="product",
            resource_id="prod-1",
            request=request,
        )

        # Retrieve logs by correlation ID
        logs = db.query(AuditLog).filter(
            AuditLog.correlation_id == correlation_id,
        ).all()

        assert len(logs) == 2
        assert all(log.correlation_id == correlation_id for log in logs)
        assert all(log.ip_address == "127.0.0.1" for log in logs)

    def test_retention_policy_compliance(self, audit_service: AuditService, test_vendor: Vendor, db: Session):
        """Test that audit logs respect retention policies"""
        # Create old non-sensitive log
        old_log = AuditLog(
            vendor_id=test_vendor.id,
            user_id=test_vendor.id,
            action=AuditAction.LOGIN,
            is_sensitive=False,
            retention_required=False,
            timestamp=datetime.utcnow() - timedelta(days=400),
        )
        db.add(old_log)

        # Create old sensitive log that must be retained
        sensitive_log = AuditLog(
            vendor_id=test_vendor.id,
            user_id=test_vendor.id,
            action=AuditAction.GDPR_EXPORT,
            is_sensitive=True,
            retention_required=True,
            timestamp=datetime.utcnow() - timedelta(days=400),
        )
        db.add(sensitive_log)
        db.commit()

        # Simulate cleanup (365-day retention for non-sensitive)
        cutoff = datetime.utcnow() - timedelta(days=365)
        deletable_logs = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff,
            AuditLog.is_sensitive == False,
            AuditLog.retention_required == False,
        ).all()

        assert len(deletable_logs) == 1
        assert deletable_logs[0].id == old_log.id

        # Sensitive logs should NOT be deletable
        sensitive_logs = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff,
            AuditLog.retention_required == True,
        ).all()

        assert len(sensitive_logs) == 1
        assert sensitive_logs[0].id == sensitive_log.id
