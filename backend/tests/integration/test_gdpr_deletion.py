"""
Integration tests for GDPR deletion functionality

Tests right to erasure (Article 17) including anonymization and legal holds.
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.gdpr_service import GDPRService
from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.gdpr_compliance import (
    DataSubjectRequest,
    DSARType,
    DSARStatus,
    LegalHold,
    DataDeletionLog,
)


@pytest.fixture
def gdpr_service(db: Session):
    """Create GDPR service instance"""
    return GDPRService(db)


@pytest.fixture
def test_vendor_with_data(db: Session):
    """Create test vendor with data for deletion"""
    vendor = Vendor(
        id="vendor-delete-test",
        email="delete@test.com",
        business_name="Delete Test Vendor",
    )
    db.add(vendor)

    # Add products
    for i in range(3):
        product = Product(
            id=f"prod-del-{i}",
            vendor_id=vendor.id,
            name=f"Product {i}",
            category="Test",
            price=10.00 + i,
        )
        db.add(product)

    # Add sales
    for i in range(5):
        sale = Sale(
            id=f"sale-del-{i}",
            vendor_id=vendor.id,
            product_id=f"prod-del-{i % 3}",
            quantity=10,
            total_amount=100.00,
            sale_date=datetime.utcnow(),
        )
        db.add(sale)

    db.commit()
    return vendor


class TestGDPRDeletion:
    """Test GDPR Article 17 - Right to erasure"""

    def test_delete_all_user_products(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion removes all user products"""
        # Verify products exist
        products_before = db.query(Product).filter(
            Product.vendor_id == test_vendor_with_data.id
        ).count()
        assert products_before == 3

        # Delete user data
        counts = gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify products deleted
        products_after = db.query(Product).filter(
            Product.vendor_id == test_vendor_with_data.id
        ).count()
        assert products_after == 0
        assert counts["products"] == 3

    def test_delete_all_user_sales(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion removes all user sales"""
        # Verify sales exist
        sales_before = db.query(Sale).filter(
            Sale.vendor_id == test_vendor_with_data.id
        ).count()
        assert sales_before == 5

        # Delete user data
        counts = gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify sales deleted
        sales_after = db.query(Sale).filter(
            Sale.vendor_id == test_vendor_with_data.id
        ).count()
        assert sales_after == 0
        assert counts["sales"] == 5

    def test_deletion_logs_created(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletions are logged for audit"""
        # Delete user data
        gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify deletion logs created
        deletion_logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.vendor_id == test_vendor_with_data.id,
        ).all()

        # Should have logs for products and sales
        assert len(deletion_logs) > 0

        data_types = [log.data_type for log in deletion_logs]
        assert "product" in data_types
        assert "sale" in data_types

    def test_legal_hold_prevents_deletion(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that active legal hold prevents deletion"""
        # Create legal hold
        legal_hold = LegalHold(
            vendor_id=test_vendor_with_data.id,
            hold_name="Investigation Hold",
            description="Data needed for investigation",
            reason="investigation",
            data_types=["sales", "products"],
            is_active=True,
        )
        db.add(legal_hold)
        db.commit()

        # Attempt deletion should fail
        with pytest.raises(ValueError, match="active legal hold"):
            gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify data NOT deleted
        products_count = db.query(Product).filter(
            Product.vendor_id == test_vendor_with_data.id
        ).count()
        assert products_count == 3

    def test_anonymization_instead_of_deletion(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test anonymization as alternative to hard deletion"""
        original_email = test_vendor_with_data.email
        original_name = test_vendor_with_data.business_name

        # Anonymize instead of delete
        counts = gdpr_service.delete_user_data(
            test_vendor_with_data.id,
            anonymize=True,
        )

        db.refresh(test_vendor_with_data)

        # Vendor should still exist but with anonymized data
        assert test_vendor_with_data.email != original_email
        assert test_vendor_with_data.business_name != original_name
        assert "deleted_" in test_vendor_with_data.email
        assert "@anonymized.local" in test_vendor_with_data.email
        assert "Deleted User" in test_vendor_with_data.business_name

    def test_anonymization_creates_deletion_log(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that anonymization is logged"""
        gdpr_service.delete_user_data(
            test_vendor_with_data.id,
            anonymize=True,
        )

        # Check deletion logs
        logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.vendor_id == test_vendor_with_data.id,
            DataDeletionLog.anonymized == True,
        ).all()

        assert len(logs) > 0

    def test_deletion_with_dsar_tracking(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test deletion linked to DSAR"""
        # Create DSAR for erasure
        dsar = gdpr_service.create_dsar(
            vendor_id=test_vendor_with_data.id,
            user_id=test_vendor_with_data.id,
            user_email=test_vendor_with_data.email,
            request_type=DSARType.ERASURE,
        )

        # Delete with DSAR reference
        gdpr_service.delete_user_data(
            test_vendor_with_data.id,
            dsar_id=dsar.id,
        )

        # Verify deletion logs reference DSAR
        logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.user_request_id == dsar.id,
        ).all()

        assert len(logs) > 0

    def test_deletion_reason_recorded(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion reason is recorded"""
        dsar = gdpr_service.create_dsar(
            vendor_id=test_vendor_with_data.id,
            user_id=test_vendor_with_data.id,
            user_email=test_vendor_with_data.email,
            request_type=DSARType.ERASURE,
        )

        gdpr_service.delete_user_data(
            test_vendor_with_data.id,
            dsar_id=dsar.id,
        )

        logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.vendor_id == test_vendor_with_data.id,
        ).first()

        assert logs.deletion_reason == "user_request"

    def test_deletion_no_cross_tenant_impact(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deleting one vendor doesn't affect others"""
        # Create second vendor
        vendor2 = Vendor(
            id="vendor-2",
            email="vendor2@test.com",
            business_name="Vendor 2",
        )
        db.add(vendor2)

        product2 = Product(
            id="prod-2-1",
            vendor_id=vendor2.id,
            name="Vendor 2 Product",
            category="Test",
            price=20.00,
        )
        db.add(product2)
        db.commit()

        # Delete first vendor
        gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify second vendor's data intact
        vendor2_products = db.query(Product).filter(
            Product.vendor_id == vendor2.id
        ).count()
        assert vendor2_products == 1

    def test_create_erasure_dsar(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test creating erasure request"""
        dsar = gdpr_service.create_dsar(
            vendor_id=test_vendor_with_data.id,
            user_id=test_vendor_with_data.id,
            user_email=test_vendor_with_data.email,
            request_type=DSARType.ERASURE,
            description="I want my data deleted",
        )

        assert dsar.request_type == DSARType.ERASURE
        assert dsar.status == DSARStatus.PENDING
        assert dsar.description == "I want my data deleted"

    def test_deletion_record_summary_captured(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion logs capture record summaries"""
        gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Check that logs have summaries
        logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.data_type == "product",
        ).first()

        assert logs is not None
        assert logs.record_summary is not None
        assert "name" in logs.record_summary

    def test_released_legal_hold_allows_deletion(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that released legal hold allows deletion"""
        # Create and release legal hold
        legal_hold = LegalHold(
            vendor_id=test_vendor_with_data.id,
            hold_name="Released Hold",
            description="Previously held data",
            reason="investigation",
            data_types=["sales"],
            is_active=False,  # Released
            released_by="admin-123",
        )
        db.add(legal_hold)
        db.commit()

        # Deletion should succeed
        counts = gdpr_service.delete_user_data(test_vendor_with_data.id)

        assert counts["products"] == 3
        assert counts["sales"] == 5

    def test_anonymize_email_deterministic(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that email anonymization is deterministic"""
        user_id = test_vendor_with_data.id

        gdpr_service.delete_user_data(user_id, anonymize=True)
        db.refresh(test_vendor_with_data)

        anonymized_email = test_vendor_with_data.email

        # Email should contain MD5 hash of user_id
        expected_hash = hashlib.md5(user_id.encode()).hexdigest()
        assert expected_hash in anonymized_email

    def test_deletion_timestamp_recorded(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion timestamp is captured"""
        before_delete = datetime.utcnow()

        gdpr_service.delete_user_data(test_vendor_with_data.id)

        after_delete = datetime.utcnow()

        logs = db.query(DataDeletionLog).filter(
            DataDeletionLog.vendor_id == test_vendor_with_data.id,
        ).first()

        assert logs.deleted_at >= before_delete
        assert logs.deleted_at <= after_delete

    def test_delete_recommendations(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that recommendations are deleted"""
        # Add recommendation
        rec = Recommendation(
            id="rec-del-1",
            vendor_id=test_vendor_with_data.id,
            product_id="prod-del-0",
            market_date=datetime.utcnow(),
            recommended_quantity=10,
            confidence_score=0.8,
        )
        db.add(rec)
        db.commit()

        # Delete
        counts = gdpr_service.delete_user_data(test_vendor_with_data.id)

        # Verify deleted
        recs_after = db.query(Recommendation).filter(
            Recommendation.vendor_id == test_vendor_with_data.id
        ).count()
        assert recs_after == 0
        assert counts["recommendations"] == 1

    def test_partial_deletion_rollback_on_error(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that deletion is atomic - all or nothing"""
        # This test verifies transaction rollback behavior
        # In case of error, no partial deletions should occur

        products_before = db.query(Product).filter(
            Product.vendor_id == test_vendor_with_data.id
        ).count()

        # Create legal hold to cause deletion to fail
        legal_hold = LegalHold(
            vendor_id=test_vendor_with_data.id,
            hold_name="Test Hold",
            description="Test",
            reason="test",
            data_types=["sales"],
            is_active=True,
        )
        db.add(legal_hold)
        db.commit()

        # Attempt deletion (should fail)
        try:
            gdpr_service.delete_user_data(test_vendor_with_data.id)
        except ValueError:
            pass

        # Verify NO data was deleted
        products_after = db.query(Product).filter(
            Product.vendor_id == test_vendor_with_data.id
        ).count()
        assert products_after == products_before

    def test_deletion_returns_counts(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that deletion returns counts of deleted records"""
        counts = gdpr_service.delete_user_data(test_vendor_with_data.id)

        assert isinstance(counts, dict)
        assert "products" in counts
        assert "sales" in counts
        assert "recommendations" in counts
        assert counts["products"] == 3
        assert counts["sales"] == 5
