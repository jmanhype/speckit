"""
Integration tests for recommendation generation

Tests the complete recommendation workflow including:
- ML model prediction
- Inventory analysis
- Market date forecasting
- Confidence scoring
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback


@pytest.fixture
def test_vendor_with_sales_history(db: Session):
    """Create vendor with sales history for recommendation testing"""
    vendor = Vendor(
        id="vendor-rec-test",
        email="recommend@test.com",
        business_name="Recommendation Test Vendor",
    )
    db.add(vendor)

    # Create product
    product = Product(
        id="prod-rec-1",
        vendor_id=vendor.id,
        name="Tomatoes",
        category="Produce",
        price=5.99,
        unit="lb",
    )
    db.add(product)

    # Create sales history (last 12 weeks)
    base_date = datetime.utcnow() - timedelta(days=84)  # 12 weeks ago

    for week in range(12):
        sale_date = base_date + timedelta(days=week * 7)

        # Simulate seasonal pattern: higher sales in summer months
        month = sale_date.month
        base_quantity = 50
        seasonal_factor = 1.2 if month in [6, 7, 8] else 1.0

        quantity = int(base_quantity * seasonal_factor)

        sale = Sale(
            id=f"sale-rec-{week}",
            vendor_id=vendor.id,
            product_id=product.id,
            quantity=quantity,
            total_amount=quantity * 5.99,
            sale_date=sale_date,
        )
        db.add(sale)

    db.commit()
    return vendor, product


class TestRecommendationGeneration:
    """Test recommendation generation workflow"""

    def test_generate_recommendation_with_sufficient_history(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test recommendation generation with 12 weeks of sales data"""
        vendor, product = test_vendor_with_sales_history

        # Import here to avoid circular imports in test setup
        from src.services.recommendation_service import RecommendationService

        rec_service = RecommendationService(db)

        # Generate recommendation for next market date
        next_market = datetime.utcnow() + timedelta(days=7)

        recommendation = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=next_market,
        )

        assert recommendation is not None
        assert recommendation.vendor_id == vendor.id
        assert recommendation.product_id == product.id
        assert recommendation.recommended_quantity > 0
        assert 0.0 <= recommendation.confidence_score <= 1.0
        assert recommendation.market_date == next_market

    def test_recommendation_uses_sales_patterns(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test that recommendations learn from historical patterns"""
        vendor, product = test_vendor_with_sales_history

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        # Get average of last 4 weeks
        recent_sales = db.query(Sale).filter(
            Sale.vendor_id == vendor.id,
            Sale.product_id == product.id,
        ).order_by(Sale.sale_date.desc()).limit(4).all()

        avg_quantity = sum(s.quantity for s in recent_sales) / len(recent_sales)

        # Generate recommendation
        next_market = datetime.utcnow() + timedelta(days=7)
        recommendation = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=next_market,
        )

        # Recommendation should be within reasonable range of average
        # Allow 50% deviation for ML model adjustments
        assert avg_quantity * 0.5 <= recommendation.recommended_quantity <= avg_quantity * 1.5

    def test_insufficient_history_returns_none_or_low_confidence(
        self,
        db: Session
    ):
        """Test behavior with insufficient sales history"""
        # Create vendor with only 1 sale
        vendor = Vendor(
            id="vendor-new",
            email="new@test.com",
            business_name="New Vendor",
        )
        db.add(vendor)

        product = Product(
            id="prod-new",
            vendor_id=vendor.id,
            name="New Product",
            category="Produce",
            price=10.00,
        )
        db.add(product)

        # Only one sale
        sale = Sale(
            id="sale-single",
            vendor_id=vendor.id,
            product_id=product.id,
            quantity=10,
            total_amount=100.00,
            sale_date=datetime.utcnow() - timedelta(days=7),
        )
        db.add(sale)
        db.commit()

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        next_market = datetime.utcnow() + timedelta(days=7)
        recommendation = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=next_market,
        )

        # Should either return None or have low confidence
        if recommendation:
            assert recommendation.confidence_score < 0.5
        # else: returning None is also acceptable behavior

    def test_multiple_recommendations_for_multiple_products(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test generating recommendations for multiple products"""
        vendor, product1 = test_vendor_with_sales_history

        # Add second product with sales
        product2 = Product(
            id="prod-rec-2",
            vendor_id=vendor.id,
            name="Lettuce",
            category="Produce",
            price=3.49,
        )
        db.add(product2)

        # Add sales for second product
        for i in range(8):
            sale = Sale(
                id=f"sale-lettuce-{i}",
                vendor_id=vendor.id,
                product_id=product2.id,
                quantity=30,
                total_amount=104.70,
                sale_date=datetime.utcnow() - timedelta(days=i * 7),
            )
            db.add(sale)
        db.commit()

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        next_market = datetime.utcnow() + timedelta(days=7)

        # Generate for both products
        rec1 = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product1.id,
            market_date=next_market,
        )

        rec2 = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product2.id,
            market_date=next_market,
        )

        assert rec1 is not None
        assert rec2 is not None
        assert rec1.product_id != rec2.product_id

    def test_recommendation_saved_to_database(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test that generated recommendations are persisted"""
        vendor, product = test_vendor_with_sales_history

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        next_market = datetime.utcnow() + timedelta(days=7)
        recommendation = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=next_market,
        )

        # Verify it's in the database
        saved_rec = db.query(Recommendation).filter(
            Recommendation.id == recommendation.id
        ).first()

        assert saved_rec is not None
        assert saved_rec.vendor_id == vendor.id
        assert saved_rec.recommended_quantity == recommendation.recommended_quantity

    def test_recommendation_feedback_submission(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test submitting feedback on recommendations"""
        vendor, product = test_vendor_with_sales_history

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        # Generate recommendation
        next_market = datetime.utcnow() + timedelta(days=7)
        recommendation = rec_service.generate_recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=next_market,
        )

        # Submit feedback
        feedback = RecommendationFeedback(
            vendor_id=vendor.id,
            recommendation_id=recommendation.id,
            actual_quantity_sold=recommendation.recommended_quantity - 2,  # Sold slightly less
            rating=4,
            was_accurate=True,
            comments="Pretty close!",
        )
        db.add(feedback)
        db.commit()

        # Verify feedback saved
        saved_feedback = db.query(RecommendationFeedback).filter(
            RecommendationFeedback.recommendation_id == recommendation.id
        ).first()

        assert saved_feedback is not None
        assert saved_feedback.rating == 4
        assert saved_feedback.was_accurate is True

    def test_recommendation_accuracy_calculation(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test calculating recommendation accuracy from feedback"""
        vendor, product = test_vendor_with_sales_history

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        # Create recommendation
        recommendation = Recommendation(
            vendor_id=vendor.id,
            product_id=product.id,
            market_date=datetime.utcnow(),
            recommended_quantity=50,
            confidence_score=0.8,
        )
        db.add(recommendation)
        db.commit()

        # Add feedback with actual = 48 (96% accuracy)
        feedback = RecommendationFeedback(
            vendor_id=vendor.id,
            recommendation_id=recommendation.id,
            actual_quantity_sold=48,
            rating=5,
            was_accurate=True,
        )
        db.add(feedback)
        db.commit()

        # Calculate accuracy
        accuracy = rec_service.calculate_accuracy(recommendation.id)

        # Should be ~96%
        assert 0.95 <= accuracy <= 0.97

    def test_batch_recommendation_generation(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test generating recommendations for all products at once"""
        vendor, product = test_vendor_with_sales_history

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        next_market = datetime.utcnow() + timedelta(days=7)

        # Generate for all vendor products
        recommendations = rec_service.generate_batch_recommendations(
            vendor_id=vendor.id,
            market_date=next_market,
        )

        assert len(recommendations) >= 1
        assert all(r.vendor_id == vendor.id for r in recommendations)
        assert all(r.market_date == next_market for r in recommendations)

    def test_recommendation_respects_tenant_isolation(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test that recommendations are tenant-isolated"""
        vendor1, product1 = test_vendor_with_sales_history

        # Create second vendor
        vendor2 = Vendor(
            id="vendor-rec-2",
            email="vendor2@test.com",
            business_name="Vendor 2",
        )
        db.add(vendor2)

        product2 = Product(
            id="prod-vendor2",
            vendor_id=vendor2.id,
            name="Product 2",
            category="Produce",
            price=10.00,
        )
        db.add(product2)
        db.commit()

        from src.services.recommendation_service import RecommendationService
        rec_service = RecommendationService(db)

        next_market = datetime.utcnow() + timedelta(days=7)

        # Generate for vendor 1
        rec1 = rec_service.generate_recommendation(
            vendor_id=vendor1.id,
            product_id=product1.id,
            market_date=next_market,
        )

        # Verify vendor 1's recommendation doesn't use vendor 2's data
        # (This is implicit in the implementation, but good to test)
        assert rec1.vendor_id == vendor1.id

        # Verify can't generate recommendation for vendor 1's product using vendor 2's ID
        # (Should either fail or return None)
        try:
            rec_cross = rec_service.generate_recommendation(
                vendor_id=vendor2.id,
                product_id=product1.id,  # Vendor 1's product
                market_date=next_market,
            )
            # If it succeeds, it should return None or raise error
            assert rec_cross is None
        except ValueError:
            # Raising an error is also acceptable
            pass

    def test_historical_recommendations_retrieval(
        self,
        test_vendor_with_sales_history,
        db: Session
    ):
        """Test retrieving historical recommendations"""
        vendor, product = test_vendor_with_sales_history

        # Create several past recommendations
        for i in range(5):
            rec = Recommendation(
                id=f"rec-hist-{i}",
                vendor_id=vendor.id,
                product_id=product.id,
                market_date=datetime.utcnow() - timedelta(days=i * 7),
                recommended_quantity=50 + i,
                confidence_score=0.8,
            )
            db.add(rec)
        db.commit()

        # Retrieve recommendations
        recs = db.query(Recommendation).filter(
            Recommendation.vendor_id == vendor.id,
            Recommendation.product_id == product.id,
        ).order_by(Recommendation.market_date.desc()).all()

        assert len(recs) == 5
        # Should be ordered by date descending
        assert recs[0].market_date > recs[-1].market_date
