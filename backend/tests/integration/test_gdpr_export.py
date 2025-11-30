"""
Integration tests for GDPR data export functionality

Tests right to access (Article 15) - complete data portability.
"""

import pytest
import json
from datetime import datetime
from sqlalchemy.orm import Session

from src.services.gdpr_service import GDPRService
from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.models.gdpr_compliance import UserConsent, DataSubjectRequest, DSARType, DSARStatus


@pytest.fixture
def gdpr_service(db: Session):
    """Create GDPR service instance"""
    return GDPRService(db)


@pytest.fixture
def test_vendor_with_data(db: Session):
    """Create test vendor with complete dataset"""
    vendor = Vendor(
        id="vendor-export-test",
        email="export@test.com",
        business_name="Export Test Vendor",
    )
    db.add(vendor)

    # Add products
    product1 = Product(
        id="prod-1",
        vendor_id=vendor.id,
        name="Tomatoes",
        category="Produce",
        price=5.99,
    )
    product2 = Product(
        id="prod-2",
        vendor_id=vendor.id,
        name="Lettuce",
        category="Produce",
        price=3.49,
    )
    db.add_all([product1, product2])

    # Add sales
    sale1 = Sale(
        id="sale-1",
        vendor_id=vendor.id,
        product_id=product1.id,
        quantity=10,
        total_amount=59.90,
        sale_date=datetime(2025, 1, 15),
    )
    sale2 = Sale(
        id="sale-2",
        vendor_id=vendor.id,
        product_id=product2.id,
        quantity=5,
        total_amount=17.45,
        sale_date=datetime(2025, 1, 20),
    )
    db.add_all([sale1, sale2])

    # Add recommendations
    rec1 = Recommendation(
        id="rec-1",
        vendor_id=vendor.id,
        product_id=product1.id,
        market_date=datetime(2025, 2, 1),
        recommended_quantity=15,
        confidence_score=0.85,
    )
    db.add(rec1)

    # Add feedback
    feedback1 = RecommendationFeedback(
        id="feedback-1",
        vendor_id=vendor.id,
        recommendation_id=rec1.id,
        actual_quantity_sold=14,
        rating=5,
        was_accurate=True,
    )
    db.add(feedback1)

    # Add consent
    consent1 = UserConsent(
        id="consent-1",
        vendor_id=vendor.id,
        user_id=vendor.id,
        user_email=vendor.email,
        consent_type="analytics",
        consent_given=True,
        consent_text="I agree to analytics tracking",
        given_at=datetime.utcnow(),
        ip_address="127.0.0.1",
    )
    db.add(consent1)

    db.commit()
    return vendor


class TestGDPRDataExport:
    """Test GDPR Article 15 - Right to access"""

    def test_export_includes_personal_information(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes basic personal information"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "personal_information" in export
        assert export["personal_information"]["email"] == "export@test.com"
        assert export["personal_information"]["name"] == "Export Test Vendor"
        assert "created_at" in export["personal_information"]

    def test_export_includes_all_products(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes all user products"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "products" in export
        assert len(export["products"]) == 2

        product_names = [p["name"] for p in export["products"]]
        assert "Tomatoes" in product_names
        assert "Lettuce" in product_names

        # Verify product details
        tomato = next(p for p in export["products"] if p["name"] == "Tomatoes")
        assert tomato["category"] == "Produce"
        assert tomato["price"] == 5.99

    def test_export_includes_all_sales(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes all sales history"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "sales" in export
        assert len(export["sales"]) == 2

        # Verify sale details
        sale_totals = [s["total_amount"] for s in export["sales"]]
        assert 59.90 in sale_totals
        assert 17.45 in sale_totals

    def test_export_includes_recommendations(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes all recommendations"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "recommendations" in export
        assert len(export["recommendations"]) == 1

        rec = export["recommendations"][0]
        assert rec["recommended_quantity"] == 15
        assert rec["confidence_score"] == 0.85

    def test_export_includes_feedback(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes recommendation feedback"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "feedback" in export
        assert len(export["feedback"]) == 1

        feedback = export["feedback"][0]
        assert feedback["actual_quantity_sold"] == 14
        assert feedback["rating"] == 5
        assert feedback["was_accurate"] is True

    def test_export_includes_consent_history(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes consent tracking"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "consents" in export
        assert len(export["consents"]) == 1

        consent = export["consents"][0]
        assert consent["consent_type"] == "analytics"
        assert consent["consent_given"] is True

    def test_export_is_machine_readable(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export can be serialized to JSON"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        # Should be JSON serializable
        json_str = json.dumps(export, indent=2)
        assert len(json_str) > 0

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["personal_information"]["email"] == "export@test.com"

    def test_export_includes_metadata(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes metadata"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        assert "export_date" in export
        assert "user_id" in export
        assert export["user_id"] == test_vendor_with_data.id

        # Export date should be ISO format
        export_date = datetime.fromisoformat(export["export_date"])
        assert isinstance(export_date, datetime)

    def test_export_for_user_with_no_data(self, gdpr_service: GDPRService, db: Session):
        """Test export for user with minimal data"""
        vendor = Vendor(
            id="vendor-empty",
            email="empty@test.com",
            business_name="Empty Vendor",
        )
        db.add(vendor)
        db.commit()

        export = gdpr_service.export_user_data(vendor.id)

        assert export["personal_information"]["email"] == "empty@test.com"
        assert len(export["products"]) == 0
        assert len(export["sales"]) == 0
        assert len(export["recommendations"]) == 0
        assert len(export["feedback"]) == 0

    def test_create_dsar_for_export(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test creating DSAR for data export"""
        dsar = gdpr_service.create_dsar(
            vendor_id=test_vendor_with_data.id,
            user_id=test_vendor_with_data.id,
            user_email=test_vendor_with_data.email,
            request_type=DSARType.ACCESS,
            description="Please provide all my data",
        )

        assert dsar.request_type == DSARType.ACCESS
        assert dsar.status == DSARStatus.PENDING
        assert dsar.user_email == "export@test.com"

        # Deadline should be 30 days from now
        deadline_days = (dsar.deadline - dsar.requested_at).days
        assert deadline_days == 30

    def test_dsar_30_day_deadline(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that DSAR has 30-day deadline per GDPR Article 12"""
        dsar = gdpr_service.create_dsar(
            vendor_id=test_vendor_with_data.id,
            user_id=test_vendor_with_data.id,
            user_email=test_vendor_with_data.email,
            request_type=DSARType.ACCESS,
        )

        days_until_deadline = (dsar.deadline - datetime.utcnow()).days
        assert 29 <= days_until_deadline <= 30  # Allow for timing

    def test_export_with_timestamps(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export includes all timestamps in ISO format"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        # Check product timestamps
        if export["products"]:
            product = export["products"][0]
            assert "created_at" in product
            # Should be parseable as datetime
            if product["created_at"]:
                dt = datetime.fromisoformat(product["created_at"])
                assert isinstance(dt, datetime)

        # Check sales timestamps
        if export["sales"]:
            sale = export["sales"][0]
            assert "sale_date" in sale
            if sale["sale_date"]:
                dt = datetime.fromisoformat(sale["sale_date"])
                assert isinstance(dt, datetime)

    def test_export_no_pii_leakage_to_other_users(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor, db: Session):
        """Test that export only includes user's own data"""
        # Create another vendor
        other_vendor = Vendor(
            id="other-vendor",
            email="other@test.com",
            business_name="Other Vendor",
        )
        db.add(other_vendor)

        # Add product for other vendor
        other_product = Product(
            id="other-prod",
            vendor_id=other_vendor.id,
            name="Other Product",
            category="Other",
            price=99.99,
        )
        db.add(other_product)
        db.commit()

        # Export first vendor's data
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        # Should NOT include other vendor's products
        product_names = [p["name"] for p in export["products"]]
        assert "Other Product" not in product_names
        assert len(export["products"]) == 2  # Only original vendor's products

    def test_export_data_completeness(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that export contains all required sections"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        required_sections = [
            "export_date",
            "user_id",
            "personal_information",
            "products",
            "sales",
            "recommendations",
            "feedback",
            "consents",
        ]

        for section in required_sections:
            assert section in export, f"Missing required section: {section}"

    def test_export_decimal_handling(self, gdpr_service: GDPRService, test_vendor_with_data: Vendor):
        """Test that Decimal fields are converted to float for JSON"""
        export = gdpr_service.export_user_data(test_vendor_with_data.id)

        # Product prices should be float
        if export["products"]:
            price = export["products"][0]["price"]
            assert isinstance(price, (float, type(None)))

        # Sale amounts should be float
        if export["sales"]:
            amount = export["sales"][0]["total_amount"]
            assert isinstance(amount, (float, type(None)))
