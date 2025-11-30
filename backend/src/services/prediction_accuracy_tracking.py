"""
Prediction accuracy tracking system

Monitors prediction quality against actual outcomes to verify
SC-002: 70% of predictions within ±20% margin of actual sales.

Tracks:
- Individual prediction accuracy
- Vendor-level accuracy rates
- Product-level accuracy
- Trend analysis over time
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AccuracyMetrics:
    """Prediction accuracy metrics"""

    total_predictions: int
    predictions_with_feedback: int
    accurate_predictions: int  # Within ±20%
    accuracy_rate: float  # Percentage
    overstock_rate: float  # Percentage overstocked
    understock_rate: float  # Percentage understocked
    avg_variance_percentage: float
    meets_success_criterion: bool  # SC-002: ≥70% accurate


class PredictionAccuracyTracker:
    """
    Service for tracking prediction accuracy

    Monitors SC-002 success criterion:
    "70% of quantity predictions within ±20% margin of actual sales"
    """

    ACCURACY_MARGIN = 0.20  # ±20% margin
    SUCCESS_THRESHOLD = 0.70  # 70% must be within margin

    def __init__(self, db: Session):
        """
        Initialize accuracy tracker

        Args:
            db: Database session
        """
        self.db = db

    def calculate_vendor_accuracy(
        self,
        vendor_id: str,
        days_back: int = 30,
    ) -> AccuracyMetrics:
        """
        Calculate prediction accuracy for a vendor

        Args:
            vendor_id: Vendor UUID
            days_back: Days of history to analyze

        Returns:
            AccuracyMetrics with accuracy statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get all feedback with actual sales for this vendor
        feedback_records = (
            self.db.query(RecommendationFeedback)
            .join(Recommendation)
            .filter(
                Recommendation.vendor_id == vendor_id,
                RecommendationFeedback.actual_quantity_sold.isnot(None),
                RecommendationFeedback.submitted_at >= cutoff_date,
            )
            .all()
        )

        # Get total recommendations made
        total_predictions = (
            self.db.query(func.count(Recommendation.id))
            .filter(
                Recommendation.vendor_id == vendor_id,
                Recommendation.created_at >= cutoff_date,
            )
            .scalar()
            or 0
        )

        if not feedback_records:
            logger.warning(f"No feedback data for vendor {vendor_id} in last {days_back} days")
            return AccuracyMetrics(
                total_predictions=total_predictions,
                predictions_with_feedback=0,
                accurate_predictions=0,
                accuracy_rate=0.0,
                overstock_rate=0.0,
                understock_rate=0.0,
                avg_variance_percentage=0.0,
                meets_success_criterion=False,
            )

        # Calculate accuracy
        accurate_count = sum(1 for f in feedback_records if f.was_accurate)
        overstock_count = sum(1 for f in feedback_records if f.was_overstocked)
        understock_count = sum(1 for f in feedback_records if f.was_understocked)

        feedback_count = len(feedback_records)
        accuracy_rate = (accurate_count / feedback_count) * 100 if feedback_count > 0 else 0

        # Calculate average variance
        variances = [
            float(f.variance_percentage)
            for f in feedback_records
            if f.variance_percentage is not None
        ]
        avg_variance = sum(variances) / len(variances) if variances else 0

        # Check success criterion
        meets_criterion = accuracy_rate >= (self.SUCCESS_THRESHOLD * 100)

        metrics = AccuracyMetrics(
            total_predictions=total_predictions,
            predictions_with_feedback=feedback_count,
            accurate_predictions=accurate_count,
            accuracy_rate=round(accuracy_rate, 2),
            overstock_rate=round((overstock_count / feedback_count) * 100, 2) if feedback_count > 0 else 0,
            understock_rate=round((understock_count / feedback_count) * 100, 2) if feedback_count > 0 else 0,
            avg_variance_percentage=round(avg_variance, 2),
            meets_success_criterion=meets_criterion,
        )

        logger.info(
            f"Accuracy for vendor {vendor_id}: {metrics.accuracy_rate}% "
            f"({metrics.accurate_predictions}/{metrics.predictions_with_feedback}), "
            f"SC-002: {'✓ PASS' if meets_criterion else '✗ FAIL'}"
        )

        return metrics

    def calculate_product_accuracy(
        self,
        vendor_id: str,
        product_id: str,
        days_back: int = 30,
    ) -> AccuracyMetrics:
        """
        Calculate prediction accuracy for a specific product

        Args:
            vendor_id: Vendor UUID
            product_id: Product UUID
            days_back: Days of history to analyze

        Returns:
            AccuracyMetrics for this product
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get feedback for this product
        feedback_records = (
            self.db.query(RecommendationFeedback)
            .join(Recommendation)
            .filter(
                Recommendation.vendor_id == vendor_id,
                Recommendation.product_id == product_id,
                RecommendationFeedback.actual_quantity_sold.isnot(None),
                RecommendationFeedback.submitted_at >= cutoff_date,
            )
            .all()
        )

        # Get total predictions for this product
        total_predictions = (
            self.db.query(func.count(Recommendation.id))
            .filter(
                Recommendation.vendor_id == vendor_id,
                Recommendation.product_id == product_id,
                Recommendation.created_at >= cutoff_date,
            )
            .scalar()
            or 0
        )

        if not feedback_records:
            return AccuracyMetrics(
                total_predictions=total_predictions,
                predictions_with_feedback=0,
                accurate_predictions=0,
                accuracy_rate=0.0,
                overstock_rate=0.0,
                understock_rate=0.0,
                avg_variance_percentage=0.0,
                meets_success_criterion=False,
            )

        accurate_count = sum(1 for f in feedback_records if f.was_accurate)
        feedback_count = len(feedback_records)
        accuracy_rate = (accurate_count / feedback_count) * 100

        variances = [
            float(f.variance_percentage)
            for f in feedback_records
            if f.variance_percentage is not None
        ]
        avg_variance = sum(variances) / len(variances) if variances else 0

        return AccuracyMetrics(
            total_predictions=total_predictions,
            predictions_with_feedback=feedback_count,
            accurate_predictions=accurate_count,
            accuracy_rate=round(accuracy_rate, 2),
            overstock_rate=0.0,  # Not calculated for product level
            understock_rate=0.0,
            avg_variance_percentage=round(avg_variance, 2),
            meets_success_criterion=accuracy_rate >= (self.SUCCESS_THRESHOLD * 100),
        )

    def calculate_overall_accuracy(self) -> AccuracyMetrics:
        """
        Calculate overall system accuracy across all vendors

        Returns:
            AccuracyMetrics for entire system
        """
        # Get all feedback with actual sales
        feedback_records = (
            self.db.query(RecommendationFeedback)
            .filter(RecommendationFeedback.actual_quantity_sold.isnot(None))
            .all()
        )

        total_predictions = self.db.query(func.count(Recommendation.id)).scalar() or 0

        if not feedback_records:
            return AccuracyMetrics(
                total_predictions=total_predictions,
                predictions_with_feedback=0,
                accurate_predictions=0,
                accuracy_rate=0.0,
                overstock_rate=0.0,
                understock_rate=0.0,
                avg_variance_percentage=0.0,
                meets_success_criterion=False,
            )

        accurate_count = sum(1 for f in feedback_records if f.was_accurate)
        overstock_count = sum(1 for f in feedback_records if f.was_overstocked)
        understock_count = sum(1 for f in feedback_records if f.was_understocked)

        feedback_count = len(feedback_records)
        accuracy_rate = (accurate_count / feedback_count) * 100

        variances = [
            float(f.variance_percentage)
            for f in feedback_records
            if f.variance_percentage is not None
        ]
        avg_variance = sum(variances) / len(variances) if variances else 0

        meets_criterion = accuracy_rate >= (self.SUCCESS_THRESHOLD * 100)

        metrics = AccuracyMetrics(
            total_predictions=total_predictions,
            predictions_with_feedback=feedback_count,
            accurate_predictions=accurate_count,
            accuracy_rate=round(accuracy_rate, 2),
            overstock_rate=round((overstock_count / feedback_count) * 100, 2),
            understock_rate=round((understock_count / feedback_count) * 100, 2),
            avg_variance_percentage=round(avg_variance, 2),
            meets_success_criterion=meets_criterion,
        )

        logger.info(
            f"Overall system accuracy: {metrics.accuracy_rate}% "
            f"({metrics.accurate_predictions}/{metrics.predictions_with_feedback}), "
            f"SC-002: {'✓ PASS' if meets_criterion else '✗ FAIL'}"
        )

        return metrics

    def get_accuracy_trend(
        self,
        vendor_id: str,
        weeks: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Get accuracy trend over time

        Args:
            vendor_id: Vendor UUID
            weeks: Number of weeks to analyze

        Returns:
            List of weekly accuracy metrics
        """
        trend = []
        now = datetime.utcnow()

        for week_offset in range(weeks, 0, -1):
            week_start = now - timedelta(weeks=week_offset)
            week_end = week_start + timedelta(weeks=1)

            # Get feedback for this week
            feedback_records = (
                self.db.query(RecommendationFeedback)
                .join(Recommendation)
                .filter(
                    Recommendation.vendor_id == vendor_id,
                    RecommendationFeedback.actual_quantity_sold.isnot(None),
                    RecommendationFeedback.submitted_at >= week_start,
                    RecommendationFeedback.submitted_at < week_end,
                )
                .all()
            )

            if not feedback_records:
                continue

            accurate_count = sum(1 for f in feedback_records if f.was_accurate)
            feedback_count = len(feedback_records)
            accuracy_rate = (accurate_count / feedback_count) * 100

            trend.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "feedback_count": feedback_count,
                "accurate_count": accurate_count,
                "accuracy_rate": round(accuracy_rate, 2),
                "meets_criterion": accuracy_rate >= (self.SUCCESS_THRESHOLD * 100),
            })

        return trend

    def get_poorly_performing_products(
        self,
        vendor_id: str,
        min_predictions: int = 5,
        accuracy_threshold: float = 50.0,
    ) -> List[Dict[str, Any]]:
        """
        Identify products with poor prediction accuracy

        Args:
            vendor_id: Vendor UUID
            min_predictions: Minimum predictions to include
            accuracy_threshold: Accuracy threshold (%)

        Returns:
            List of products with accuracy below threshold
        """
        # Get all products with feedback
        products = (
            self.db.query(Recommendation.product_id)
            .join(RecommendationFeedback)
            .filter(
                Recommendation.vendor_id == vendor_id,
                RecommendationFeedback.actual_quantity_sold.isnot(None),
            )
            .distinct()
            .all()
        )

        poor_performers = []

        for (product_id,) in products:
            metrics = self.calculate_product_accuracy(vendor_id, product_id)

            if (
                metrics.predictions_with_feedback >= min_predictions
                and metrics.accuracy_rate < accuracy_threshold
            ):
                poor_performers.append({
                    "product_id": product_id,
                    "predictions_with_feedback": metrics.predictions_with_feedback,
                    "accuracy_rate": metrics.accuracy_rate,
                    "avg_variance_percentage": metrics.avg_variance_percentage,
                })

        # Sort by accuracy (worst first)
        poor_performers.sort(key=lambda x: x["accuracy_rate"])

        return poor_performers


# Scheduled task for accuracy monitoring
def monitor_prediction_accuracy(db: Session) -> Dict[str, Any]:
    """
    Monitor overall system prediction accuracy

    Run this as a scheduled task (e.g., daily) to track SC-002 compliance.

    Args:
        db: Database session

    Returns:
        Accuracy monitoring report
    """
    logger.info("Starting prediction accuracy monitoring")

    tracker = PredictionAccuracyTracker(db)

    # Get overall accuracy
    overall_metrics = tracker.calculate_overall_accuracy()

    # Get vendor-level accuracy
    vendors = (
        db.query(Recommendation.vendor_id)
        .distinct()
        .all()
    )

    vendor_metrics = []
    for (vendor_id,) in vendors:
        metrics = tracker.calculate_vendor_accuracy(vendor_id)
        if metrics.predictions_with_feedback > 0:
            vendor_metrics.append({
                "vendor_id": vendor_id,
                "accuracy_rate": metrics.accuracy_rate,
                "predictions_with_feedback": metrics.predictions_with_feedback,
                "meets_criterion": metrics.meets_success_criterion,
            })

    # Identify vendors not meeting SC-002
    failing_vendors = [
        v for v in vendor_metrics
        if not v["meets_criterion"] and v["predictions_with_feedback"] >= 10
    ]

    report = {
        "monitored_at": datetime.utcnow().isoformat(),
        "overall_accuracy": {
            "accuracy_rate": overall_metrics.accuracy_rate,
            "predictions_with_feedback": overall_metrics.predictions_with_feedback,
            "meets_sc002": overall_metrics.meets_success_criterion,
        },
        "vendor_count": len(vendor_metrics),
        "vendors_meeting_sc002": sum(1 for v in vendor_metrics if v["meets_criterion"]),
        "vendors_failing_sc002": len(failing_vendors),
        "failing_vendors": failing_vendors[:10],  # Top 10 failing vendors
    }

    if not overall_metrics.meets_success_criterion:
        logger.warning(
            f"⚠️ System accuracy below SC-002 threshold: {overall_metrics.accuracy_rate}% "
            f"(need ≥{tracker.SUCCESS_THRESHOLD * 100}%)"
        )
    else:
        logger.info(
            f"✓ System accuracy meets SC-002: {overall_metrics.accuracy_rate}%"
        )

    return report
