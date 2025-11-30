"""Integration tests for venue-specific predictions.

Tests end-to-end venue-based recommendation flow:
- Venue creation and management
- Venue-specific sales tracking
- Different recommendations for different venues
- Confidence indicators for new/stale venues
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.venue import Venue
from src.models.recommendation import Recommendation
from src.services.ml_recommendations import MLRecommendationService


class TestVenueSpecificPredictions:
    """Integration tests for venue-specific ML predictions."""

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
    def venue_high_traffic(self, db_session, vendor):
        """Create high-traffic venue (farmers market downtown)."""
        venue = Venue(
            vendor_id=vendor.id,
            name="Downtown Farmers Market",
            location="123 Main St, San Francisco, CA",
            latitude=37.7749,
            longitude=-122.4194,
            typical_attendance=500,
            notes="High-traffic urban market",
        )
        db_session.add(venue)
        db_session.commit()
        db_session.refresh(venue)
        return venue

    @pytest.fixture
    def venue_low_traffic(self, db_session, vendor):
        """Create low-traffic venue (neighborhood market)."""
        venue = Venue(
            vendor_id=vendor.id,
            name="Neighborhood Market",
            location="456 Oak St, San Francisco, CA",
            latitude=37.7849,
            longitude=-122.4294,
            typical_attendance=100,
            notes="Small neighborhood market",
        )
        db_session.add(venue)
        db_session.commit()
        db_session.refresh(venue)
        return venue

    @pytest.fixture
    def product(self, db_session, vendor):
        """Create test product."""
        product = Product(
            vendor_id=vendor.id,
            name="Sourdough Bread",
            price=Decimal("8.00"),
            category="Bakery",
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    def create_sales_history(
        self,
        db_session,
        vendor,
        venue,
        product,
        num_days=30,
        avg_quantity=20,
    ):
        """Create historical sales data for a venue."""
        today = datetime.utcnow()

        for i in range(num_days):
            sale_date = today - timedelta(days=i + 1)

            sale = Sale(
                vendor_id=vendor.id,
                sale_date=sale_date,
                total_amount=Decimal(avg_quantity) * Decimal("8.00"),
                square_location_id=str(venue.id),  # Link to venue
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

    def test_create_venue(self, db_session, vendor):
        """Test venue creation."""
        venue = Venue(
            vendor_id=vendor.id,
            name="Test Market",
            location="789 Test St",
            latitude=37.7,
            longitude=-122.4,
        )
        db_session.add(venue)
        db_session.commit()

        # Verify venue saved
        assert venue.id is not None
        assert venue.name == "Test Market"

    def test_different_venues_different_recommendations(
        self,
        db_session,
        vendor,
        venue_high_traffic,
        venue_low_traffic,
        product,
    ):
        """Test that different venues get different recommendations."""
        # Create sales history: high-traffic venue sells 40/day, low-traffic sells 10/day
        self.create_sales_history(
            db_session,
            vendor,
            venue_high_traffic,
            product,
            num_days=30,
            avg_quantity=40,
        )

        self.create_sales_history(
            db_session,
            vendor,
            venue_low_traffic,
            product,
            num_days=30,
            avg_quantity=10,
        )

        # Generate recommendations for next week
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        market_date = datetime.utcnow() + timedelta(days=7)

        rec_high = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=venue_high_traffic.id,
            market_date=market_date,
        )

        rec_low = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=venue_low_traffic.id,
            market_date=market_date,
        )

        # High-traffic venue should get higher recommendation
        assert rec_high.recommended_quantity > rec_low.recommended_quantity
        assert rec_high.venue_id == venue_high_traffic.id
        assert rec_low.venue_id == venue_low_traffic.id

    def test_new_venue_low_confidence(self, db_session, vendor, product):
        """Test that new venue (no sales history) has low confidence."""
        # Create new venue with no sales
        new_venue = Venue(
            vendor_id=vendor.id,
            name="Brand New Market",
            location="999 New St",
            latitude=37.8,
            longitude=-122.5,
        )
        db_session.add(new_venue)
        db_session.commit()
        db_session.refresh(new_venue)

        # Generate recommendation
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        market_date = datetime.utcnow() + timedelta(days=7)

        rec = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=new_venue.id,
            market_date=market_date,
        )

        # New venue should have low confidence (<0.5)
        assert rec.confidence_score < Decimal("0.5")
        assert rec.venue_id == new_venue.id

    def test_established_venue_high_confidence(
        self,
        db_session,
        vendor,
        venue_high_traffic,
        product,
    ):
        """Test that established venue (20+ sales) has high confidence."""
        # Create 25 sales over past 30 days
        self.create_sales_history(
            db_session,
            vendor,
            venue_high_traffic,
            product,
            num_days=25,
            avg_quantity=30,
        )

        # Generate recommendation
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        market_date = datetime.utcnow() + timedelta(days=7)

        rec = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=venue_high_traffic.id,
            market_date=market_date,
        )

        # Established venue should have high confidence (>=0.7)
        assert rec.confidence_score >= Decimal("0.7")

    def test_stale_venue_medium_confidence(
        self,
        db_session,
        vendor,
        venue_high_traffic,
        product,
    ):
        """Test that stale venue (last sale 6+ months ago) has medium confidence."""
        # Create sales but all 7+ months ago
        today = datetime.utcnow()
        for i in range(20):
            sale_date = today - timedelta(days=210 + i)  # 7+ months ago

            sale = Sale(
                vendor_id=vendor.id,
                sale_date=sale_date,
                total_amount=Decimal("240.00"),
                square_location_id=str(venue_high_traffic.id),
                line_items=[
                    {
                        "product_id": str(product.id),
                        "quantity": "30",
                        "name": product.name,
                    }
                ],
            )
            db_session.add(sale)

        db_session.commit()

        # Generate recommendation
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        market_date = datetime.utcnow() + timedelta(days=7)

        rec = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=venue_high_traffic.id,
            market_date=market_date,
        )

        # Stale venue should have medium confidence (0.3-0.6)
        assert Decimal("0.3") <= rec.confidence_score <= Decimal("0.6")

    def test_seasonal_product_detection(
        self,
        db_session,
        vendor,
        venue_high_traffic,
    ):
        """Test that seasonal products are detected based on sales patterns."""
        # Create winter product (hot soup)
        winter_product = Product(
            vendor_id=vendor.id,
            name="Hot Soup",
            price=Decimal("10.00"),
            category="Soups",
            is_active=True,
        )
        db_session.add(winter_product)
        db_session.commit()
        db_session.refresh(winter_product)

        # Create sales: high in winter (Dec-Feb), low in summer (Jun-Aug)
        today = datetime.utcnow()

        # Winter sales (30 units/day)
        for i in range(10):
            sale_date = datetime(2023, 12, i + 1)
            sale = Sale(
                vendor_id=vendor.id,
                sale_date=sale_date,
                total_amount=Decimal("300.00"),
                square_location_id=str(venue_high_traffic.id),
                line_items=[
                    {
                        "product_id": str(winter_product.id),
                        "quantity": "30",
                        "name": winter_product.name,
                    }
                ],
            )
            db_session.add(sale)

        # Summer sales (5 units/day)
        for i in range(10):
            sale_date = datetime(2024, 7, i + 1)
            sale = Sale(
                vendor_id=vendor.id,
                sale_date=sale_date,
                total_amount=Decimal("50.00"),
                square_location_id=str(venue_high_traffic.id),
                line_items=[
                    {
                        "product_id": str(winter_product.id),
                        "quantity": "5",
                        "name": winter_product.name,
                    }
                ],
            )
            db_session.add(sale)

        db_session.commit()

        # Generate recommendations for winter vs summer
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)

        winter_date = datetime(2024, 12, 15)
        summer_date = datetime(2024, 8, 15)

        rec_winter = ml_service.generate_recommendation(
            product_id=winter_product.id,
            venue_id=venue_high_traffic.id,
            market_date=winter_date,
        )

        rec_summer = ml_service.generate_recommendation(
            product_id=winter_product.id,
            venue_id=venue_high_traffic.id,
            market_date=summer_date,
        )

        # Winter recommendation should be much higher than summer
        assert rec_winter.recommended_quantity > rec_summer.recommended_quantity * 2

    def test_venue_features_stored_in_recommendation(
        self,
        db_session,
        vendor,
        venue_high_traffic,
        product,
    ):
        """Test that venue-specific features are stored in recommendation."""
        # Create some sales history
        self.create_sales_history(
            db_session,
            vendor,
            venue_high_traffic,
            product,
            num_days=20,
            avg_quantity=25,
        )

        # Generate recommendation
        ml_service = MLRecommendationService(vendor_id=vendor.id, db=db_session)
        market_date = datetime.utcnow() + timedelta(days=7)

        rec = ml_service.generate_recommendation(
            product_id=product.id,
            venue_id=venue_high_traffic.id,
            market_date=market_date,
        )

        # Should have venue_features stored
        assert 'venue_avg_sales' in rec.historical_features
        assert 'venue_sales_count' in rec.historical_features
        assert rec.historical_features['venue_avg_sales'] > 0
