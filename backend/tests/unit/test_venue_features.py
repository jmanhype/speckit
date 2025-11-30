"""Unit tests for venue-specific feature engineering.

Tests venue-based ML features including:
- Venue performance metrics
- Seasonal product detection
- Confidence scoring for new/stale venues
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.services.ml_recommendations import MLRecommendationService, VenueFeatureEngineer


class TestVenueFeatureEngineer:
    """Test venue-specific feature engineering."""

    @pytest.fixture
    def vendor_id(self):
        """Test vendor ID."""
        return uuid4()

    @pytest.fixture
    def venue_id_a(self):
        """Test venue A ID."""
        return uuid4()

    @pytest.fixture
    def venue_id_b(self):
        """Test venue B ID."""
        return uuid4()

    @pytest.fixture
    def product_id(self):
        """Test product ID."""
        return uuid4()

    @pytest.fixture
    def engineer(self, db_session, vendor_id):
        """Create venue feature engineer."""
        return VenueFeatureEngineer(vendor_id=vendor_id, db=db_session)

    def test_venue_performance_features(self, engineer, venue_id_a, product_id):
        """Test extraction of venue-specific performance features."""
        # This test will fail until we implement venue features
        market_date = datetime(2024, 6, 15, 10, 0)

        features = engineer.extract_venue_features(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        # Should include venue-specific metrics
        assert 'venue_avg_sales' in features
        assert 'venue_max_sales' in features
        assert 'venue_sales_count' in features
        assert 'venue_last_sale_days_ago' in features

    def test_venue_different_performance_patterns(self, engineer, venue_id_a, venue_id_b, product_id, db_session):
        """Test that different venues produce different features."""
        # Create sample sales data for two venues
        # Venue A: high performance
        # Venue B: low performance

        market_date = datetime(2024, 6, 15, 10, 0)

        features_a = engineer.extract_venue_features(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        features_b = engineer.extract_venue_features(
            venue_id=venue_id_b,
            product_id=product_id,
            market_date=market_date,
        )

        # Features should differ between venues
        # (This will fail until we have test data)
        assert features_a != features_b

    def test_seasonal_product_detection(self, engineer, product_id):
        """Test detection of seasonal products."""
        # Test winter product (soup, hot drinks)
        winter_month = 12
        summer_month = 7

        is_seasonal_winter = engineer.is_seasonal_product(
            product_id=product_id,
            month=winter_month,
        )

        is_seasonal_summer = engineer.is_seasonal_product(
            product_id=product_id,
            month=summer_month,
        )

        # Should identify seasonality based on sales patterns
        # (Will fail until implemented)
        assert isinstance(is_seasonal_winter, bool)
        assert isinstance(is_seasonal_summer, bool)

    def test_seasonal_features_added_to_model(self, engineer, product_id, venue_id_a):
        """Test that seasonal features are included in feature set."""
        market_date = datetime(2024, 12, 15, 10, 0)  # Winter

        features = engineer.extract_venue_features(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        assert 'is_seasonal' in features
        assert 'seasonal_strength' in features
        assert 'month_avg_sales' in features

    def test_confidence_score_new_venue(self, engineer, venue_id_a, product_id):
        """Test confidence scoring for venue with no history."""
        market_date = datetime(2024, 6, 15, 10, 0)

        confidence = engineer.calculate_venue_confidence(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        # New venue should have low confidence
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Low confidence for new venue

    def test_confidence_score_established_venue(self, engineer, venue_id_a, product_id, db_session):
        """Test confidence scoring for venue with good history."""
        # Create 20+ sales at this venue over past 6 months
        # (Will fail until we have test data setup)

        market_date = datetime.utcnow() + timedelta(days=7)

        confidence = engineer.calculate_venue_confidence(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        # Established venue should have high confidence
        assert confidence >= 0.7

    def test_confidence_score_stale_venue(self, engineer, venue_id_a, product_id, db_session):
        """Test confidence scoring for venue with no recent sales (6+ months)."""
        market_date = datetime.utcnow() + timedelta(days=7)

        # Venue has sales but all > 6 months old
        confidence = engineer.calculate_venue_confidence(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        # Stale venue should have medium confidence (better than new, worse than active)
        assert 0.3 <= confidence <= 0.6

    def test_venue_embedding_generation(self, engineer, venue_id_a):
        """Test generation of venue embeddings for ML model."""
        embedding = engineer.generate_venue_embedding(venue_id=venue_id_a)

        # Should produce numerical embedding vector
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)

    def test_venue_features_with_insufficient_data(self, engineer, venue_id_a, product_id):
        """Test graceful handling when venue has < 3 sales."""
        market_date = datetime(2024, 6, 15, 10, 0)

        features = engineer.extract_venue_features(
            venue_id=venue_id_a,
            product_id=product_id,
            market_date=market_date,
        )

        # Should return default features rather than crash
        assert features is not None
        assert 'venue_avg_sales' in features
        # With insufficient data, avg should be 0 or default value
        assert features['venue_avg_sales'] >= 0


class TestMLRecommendationServiceVenueEnhancements:
    """Test ML service with venue-specific enhancements."""

    @pytest.fixture
    def vendor_id(self):
        """Test vendor ID."""
        return uuid4()

    @pytest.fixture
    def venue_id(self):
        """Test venue ID."""
        return uuid4()

    @pytest.fixture
    def product_id(self):
        """Test product ID."""
        return uuid4()

    @pytest.fixture
    def ml_service(self, db_session, vendor_id):
        """Create ML recommendation service."""
        return MLRecommendationService(vendor_id=vendor_id, db=db_session)

    def test_generate_recommendation_with_venue(self, ml_service, product_id, venue_id):
        """Test recommendation generation includes venue features."""
        market_date = datetime(2024, 6, 15, 10, 0)

        recommendation = ml_service.generate_recommendation(
            product_id=product_id,
            venue_id=venue_id,  # New parameter
            market_date=market_date,
        )

        # Should include venue context
        assert recommendation.venue_id == venue_id
        assert 'venue_avg_sales' in recommendation.historical_features

    def test_different_venues_produce_different_recommendations(
        self, ml_service, product_id, db_session
    ):
        """Test that same product gets different recommendations for different venues."""
        venue_a = uuid4()
        venue_b = uuid4()
        market_date = datetime(2024, 6, 15, 10, 0)

        # Generate for venue A
        rec_a = ml_service.generate_recommendation(
            product_id=product_id,
            venue_id=venue_a,
            market_date=market_date,
        )

        # Generate for venue B
        rec_b = ml_service.generate_recommendation(
            product_id=product_id,
            venue_id=venue_b,
            market_date=market_date,
        )

        # Recommendations should differ
        # (Will fail until we have proper test data)
        assert rec_a.recommended_quantity != rec_b.recommended_quantity or \
               rec_a.confidence_score != rec_b.confidence_score

    def test_seasonal_product_adjusted_for_season(self, ml_service, product_id, venue_id):
        """Test that seasonal products get adjusted recommendations."""
        winter_date = datetime(2024, 12, 15, 10, 0)
        summer_date = datetime(2024, 7, 15, 10, 0)

        rec_winter = ml_service.generate_recommendation(
            product_id=product_id,
            venue_id=venue_id,
            market_date=winter_date,
        )

        rec_summer = ml_service.generate_recommendation(
            product_id=product_id,
            venue_id=venue_id,
            market_date=summer_date,
        )

        # For seasonal products, quantities should differ by season
        # (This test will fail until seasonal detection is implemented)
        assert rec_winter.recommended_quantity != rec_summer.recommended_quantity
