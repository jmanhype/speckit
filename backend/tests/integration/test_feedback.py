"""
Integration tests for feedback submission

Tests the complete feedback workflow:
- Submitting feedback for recommendations
- Variance calculation
- Accuracy tracking
- Statistics aggregation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.models.product import Product
from src.database import get_db


client = TestClient(app)


@pytest.fixture
def vendor_id():
    """Fixture for test vendor ID"""
    return str(uuid4())


@pytest.fixture
def auth_headers(vendor_id):
    """Fixture for authentication headers"""
    # In real tests, generate valid JWT token
    return {"Authorization": f"Bearer test_token_for_{vendor_id}"}


@pytest.fixture
def test_recommendation(db: Session, vendor_id: str):
    """Fixture to create test recommendation"""
    product = Product(
        vendor_id=vendor_id,
        name="Test Sourdough Bread",
        square_id="sq_test_product",
    )
    db.add(product)
    db.commit()

    recommendation = Recommendation(
        vendor_id=vendor_id,
        product_id=product.id,
        market_date=datetime.utcnow() + timedelta(days=1),
        recommended_quantity=24,
        confidence="high",
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return recommendation


class TestFeedbackSubmission:
    """Test feedback submission workflow"""

    def test_submit_feedback_success(
        self, db: Session, test_recommendation, auth_headers
    ):
        """Test successful feedback submission"""
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 20,
                "actual_quantity_brought": 24,
                "actual_revenue": 120.00,
                "rating": 5,
                "comments": "Accurate recommendation!",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["recommendation_id"] == str(test_recommendation.id)
        assert data["actual_quantity_sold"] == 20
        assert data["rating"] == 5
        assert data["was_accurate"] is True  # Within ±20% margin

    def test_submit_feedback_calculates_variance(
        self, db: Session, test_recommendation, auth_headers
    ):
        """Test that variance is calculated correctly"""
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 30,  # +25% over recommendation
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Variance: (30 - 24) / 24 = 0.25 = 25%
        assert abs(data["variance_percentage"] - 25.0) < 0.1
        assert data["was_overstocked"] is True

    def test_submit_feedback_duplicate_fails(
        self, db: Session, test_recommendation, auth_headers
    ):
        """Test that duplicate feedback is rejected"""
        # Submit first feedback
        client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 20,
            },
            headers=auth_headers,
        )

        # Try to submit duplicate
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 25,
            },
            headers=auth_headers,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_submit_feedback_invalid_recommendation(self, auth_headers):
        """Test feedback for non-existent recommendation"""
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(uuid4()),
                "actual_quantity_sold": 20,
            },
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestFeedbackStatistics:
    """Test feedback statistics calculation"""

    def test_get_feedback_stats(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test feedback statistics endpoint"""
        # Create multiple feedback records
        for i, (sold, rating) in enumerate([(20, 5), (22, 4), (18, 5)]):
            rec = Recommendation(
                vendor_id=vendor_id,
                product_id=test_recommendation.product_id,
                market_date=datetime.utcnow() + timedelta(days=i),
                recommended_quantity=20,
            )
            db.add(rec)
            db.commit()

            feedback = RecommendationFeedback(
                vendor_id=vendor_id,
                recommendation_id=rec.id,
                actual_quantity_sold=sold,
                rating=rating,
            )
            feedback.calculate_variance(20)
            db.add(feedback)

        db.commit()

        # Get stats
        response = client.get("/feedback/stats", headers=auth_headers)

        assert response.status_code == 200
        stats = response.json()

        assert stats["total_feedback_count"] == 3
        assert stats["avg_rating"] >= 4.0
        assert stats["accuracy_rate"] == 100.0  # All within ±20%

    def test_feedback_stats_empty(self, auth_headers):
        """Test stats with no feedback"""
        response = client.get("/feedback/stats", headers=auth_headers)

        assert response.status_code == 200
        stats = response.json()

        assert stats["total_feedback_count"] == 0
        assert stats["avg_rating"] is None


class TestFeedbackListing:
    """Test feedback listing and retrieval"""

    def test_list_feedback(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test listing feedback entries"""
        # Create feedback
        feedback = RecommendationFeedback(
            vendor_id=vendor_id,
            recommendation_id=test_recommendation.id,
            actual_quantity_sold=20,
            rating=5,
        )
        db.add(feedback)
        db.commit()

        response = client.get("/feedback", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        assert data[0]["recommendation_id"] == str(test_recommendation.id)

    def test_get_feedback_by_id(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test getting specific feedback entry"""
        feedback = RecommendationFeedback(
            vendor_id=vendor_id,
            recommendation_id=test_recommendation.id,
            actual_quantity_sold=20,
        )
        db.add(feedback)
        db.commit()

        response = client.get(f"/feedback/{feedback.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(feedback.id)
        assert data["actual_quantity_sold"] == 20


class TestFeedbackAccuracyTracking:
    """Test accuracy tracking with feedback"""

    def test_accurate_prediction_flagged(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test that accurate predictions are flagged"""
        # Submit feedback within ±20%
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 22,  # Recommended: 24, within range
            },
            headers=auth_headers,
        )

        data = response.json()
        assert data["was_accurate"] is True
        assert data["was_overstocked"] is False
        assert data["was_understocked"] is False

    def test_overstock_flagged(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test that overstocking is flagged"""
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 10,  # Recommended: 24, significantly under
            },
            headers=auth_headers,
        )

        data = response.json()
        assert data["was_accurate"] is False
        assert data["was_overstocked"] is True

    def test_understock_flagged(
        self, db: Session, test_recommendation, vendor_id, auth_headers
    ):
        """Test that understocking is flagged"""
        response = client.post(
            "/feedback",
            json={
                "recommendation_id": str(test_recommendation.id),
                "actual_quantity_sold": 35,  # Recommended: 24, significantly over
            },
            headers=auth_headers,
        )

        data = response.json()
        assert data["was_accurate"] is False
        assert data["was_understocked"] is True


# Additional test scenarios:
# - Pagination for large feedback lists
# - Filtering by date range
# - Testing with missing optional fields
# - Edge cases (negative values, zero quantities)
# - Concurrent feedback submissions
# - Feedback with very large variance values
