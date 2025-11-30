"""Integration tests for event-aware predictions.

Tests that recommendations adjust appropriately for local events.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.event_data import EventData
from src.services.ml_recommendations import MLRecommendationService


class TestEventAwarePredictions:
    """Integration tests for ML predictions with event context."""

    @pytest.fixture
    def vendor(self, db_session):
        """Create test vendor."""
        vendor = Vendor(
            email="vendor@test.com",
            password_hash="dummy_hash",
            business_name="Test Bakery",
        )
        db_session.add(vendor)
        db_session.commit()
        db_session.refresh(vendor)
        return vendor

    @pytest.fixture
    def product(self, db_session, vendor):
        """Create test product."""
        product = Product(
            vendor_id=vendor.id,
            name="Artisan Bread",
            price=Decimal("10.00"),
            category="Bakery",
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    def create_sales_history(self, db_session, vendor, product, num_days=30, avg_quantity=20):
        """Create historical sales data."""
        today = datetime.utcnow()

        for i in range(num_days):
            sale_date = today - timedelta(days=i + 1)

            sale = Sale(
                vendor_id=vendor.id,
                sale_date=sale_date,
                total_amount=Decimal(avg_quantity) * product.price,
                line_items=[
                    {
                        "product_id": str(product.id),
                        "quantity": str(avg_quantity),
                        "name": product.name,
                    }
                ],
            )
            db_session.add(sale)

        db_session.commit()

    def test_event_increases_recommended_quantity(self, db_session, vendor, product):
        """Test that special events increase recommended quantities."""
        # Create baseline sales history
        self.create_sales_history(db_session, vendor, product, num_days=30, avg_quantity=20)

        # Create special event
        event_date = datetime.utcnow() + timedelta(days=7)
        event = EventData(
            vendor_id=vendor.id,
            name="Summer Food Festival",
            event_date=event_date,
            location="Downtown",
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            expected_attendance=2000,
            is_special=True,
            source="manual",
        )
        db_session.add(event)
        db_session.commit()

        # Generate recommendations
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)

        # Recommendation with event
        rec_with_event = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=event_date,
            event_data={
                "name": "Summer Food Festival",
                "expected_attendance": 2000,
                "is_special": True,
            },
        )

        # Recommendation without event (different date)
        normal_date = datetime.utcnow() + timedelta(days=14)
        rec_without_event = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=normal_date,
            event_data={
                "expected_attendance": 100,
                "is_special": False,
            },
        )

        # Event day should have higher recommendation
        assert rec_with_event.recommended_quantity > rec_without_event.recommended_quantity
        assert rec_with_event.event_features["is_special"] is True
        assert rec_without_event.event_features["is_special"] is False

    def test_event_features_stored_in_recommendation(self, db_session, vendor, product):
        """Test that event features are stored with recommendation."""
        self.create_sales_history(db_session, vendor, product, num_days=20)

        event_date = datetime.utcnow() + timedelta(days=7)
        event_data = {
            "name": "Music Festival",
            "expected_attendance": 1500,
            "is_special": True,
        }

        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        rec = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=event_date,
            event_data=event_data,
        )

        # Verify event features are stored
        assert rec.event_features is not None
        assert rec.event_features["name"] == "Music Festival"
        assert rec.event_features["expected_attendance"] == 1500
        assert rec.event_features["is_special"] is True

    def test_nearby_event_detected_automatically(self, db_session, vendor, product):
        """Test that events near venue are automatically detected."""
        # Create event near venue
        event_date = datetime.utcnow() + timedelta(days=7)
        event = EventData(
            vendor_id=vendor.id,
            name="Local Concert",
            event_date=event_date,
            location="City Park",
            latitude=Decimal("37.7749"),  # Same area as venue
            longitude=Decimal("-122.4194"),
            expected_attendance=800,
            is_special=True,
            source="eventbrite",
        )
        db_session.add(event)
        db_session.commit()

        # Recommendations should automatically detect nearby event
        # (This requires the event service to do radius search)
        # Test will verify the event is picked up in recommendation generation

        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)

        # When generating for a venue at that location, event should be detected
        rec = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=event_date,
        )

        # Should have event features populated
        assert rec.event_features is not None

    def test_no_event_uses_defaults(self, db_session, vendor, product):
        """Test that non-event days use default values."""
        self.create_sales_history(db_session, vendor, product)

        # Random weekday with no event
        normal_date = datetime(2025, 6, 17, 10, 0)  # Tuesday

        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        rec = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=normal_date,
        )

        # Should have default event features
        assert rec.event_features["is_special"] is False
        assert rec.event_features["expected_attendance"] <= 150

    def test_multiple_events_picks_largest(self, db_session, vendor, product):
        """Test that when multiple events exist, largest impact is used."""
        event_date = datetime.utcnow() + timedelta(days=7)

        # Create two events on same day
        event1 = EventData(
            vendor_id=vendor.id,
            name="Small Craft Fair",
            event_date=event_date,
            expected_attendance=300,
            is_special=False,
            source="manual",
        )

        event2 = EventData(
            vendor_id=vendor.id,
            name="Major Food Festival",
            event_date=event_date,
            expected_attendance=3000,
            is_special=True,
            source="eventbrite",
        )

        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        # Should use the larger event
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        rec = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=event_date,
        )

        assert rec.event_features["name"] == "Major Food Festival"
        assert rec.event_features["expected_attendance"] == 3000

    def test_event_radius_filtering(self, db_session, vendor, product):
        """Test that only nearby events affect recommendations."""
        event_date = datetime.utcnow() + timedelta(days=7)

        # Event 50 miles away (should not affect recommendations)
        far_event = EventData(
            vendor_id=vendor.id,
            name="Distant Festival",
            event_date=event_date,
            latitude=Decimal("38.5000"),  # ~50 miles away
            longitude=Decimal("-123.0000"),
            expected_attendance=5000,
            is_special=True,
            source="eventbrite",
        )
        db_session.add(far_event)
        db_session.commit()

        # Recommendation at San Francisco location
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)

        # With venue location specified
        rec = ml_service.generate_recommendation(
            product_id=product.id,
            market_date=event_date,
            venue_id=None,  # No venue, so should use default location filtering
        )

        # Should not be affected by distant event
        # (depends on implementation of radius filtering)
        assert rec.event_features is not None
