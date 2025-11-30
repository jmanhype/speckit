"""
Analytics and user metrics collection service

Tracks metrics for success criteria:
- SC-003: 80% user satisfaction rating
- SC-008: 90% task completion for primary workflows
- SC-012: 60% adoption rate among active markets

Also tracks:
- User engagement
- Feature usage
- Recommendation usage rates
- Conversion rates
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct

from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.models.product import Product
from src.models.venue import Venue
from src.models.vendor import Vendor
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class UserMetrics:
    """User engagement and satisfaction metrics"""

    # SC-003: User satisfaction (≥80% target)
    avg_rating: float
    total_ratings: int
    satisfaction_rate: float  # % with rating ≥4/5
    meets_sc003: bool

    # SC-008: Task completion (≥90% target)
    task_completion_rate: float
    meets_sc008: bool

    # SC-012: Adoption rate (≥60% target)
    adoption_rate: float
    active_vendors: int
    total_vendors: int
    meets_sc012: bool

    # Additional engagement metrics
    recommendations_generated: int
    recommendations_used: int  # With feedback
    conversion_rate: float  # % recommendations with feedback


class AnalyticsService:
    """
    Service for collecting and analyzing user metrics

    Monitors success criteria:
    - SC-003: 80% user satisfaction (4+ stars)
    - SC-008: 90% task completion
    - SC-012: 60% adoption rate
    """

    SC003_TARGET = 0.80  # 80% satisfaction
    SC008_TARGET = 0.90  # 90% task completion
    SC012_TARGET = 0.60  # 60% adoption

    def __init__(self, db: Session):
        """
        Initialize analytics service

        Args:
            db: Database session
        """
        self.db = db

    def collect_user_metrics(
        self,
        days_back: int = 30,
    ) -> UserMetrics:
        """
        Collect comprehensive user metrics

        Args:
            days_back: Days of history to analyze

        Returns:
            UserMetrics with all success criterion metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # SC-003: User satisfaction
        satisfaction_metrics = self._calculate_satisfaction(cutoff_date)

        # SC-008: Task completion
        task_completion = self._calculate_task_completion(cutoff_date)

        # SC-012: Adoption rate
        adoption_metrics = self._calculate_adoption_rate(cutoff_date)

        # Additional metrics
        engagement = self._calculate_engagement(cutoff_date)

        metrics = UserMetrics(
            # SC-003
            avg_rating=satisfaction_metrics["avg_rating"],
            total_ratings=satisfaction_metrics["total_ratings"],
            satisfaction_rate=satisfaction_metrics["satisfaction_rate"],
            meets_sc003=satisfaction_metrics["satisfaction_rate"] >= self.SC003_TARGET * 100,
            # SC-008
            task_completion_rate=task_completion,
            meets_sc008=task_completion >= self.SC008_TARGET * 100,
            # SC-012
            adoption_rate=adoption_metrics["adoption_rate"],
            active_vendors=adoption_metrics["active_vendors"],
            total_vendors=adoption_metrics["total_vendors"],
            meets_sc012=adoption_metrics["adoption_rate"] >= self.SC012_TARGET * 100,
            # Engagement
            recommendations_generated=engagement["recommendations_generated"],
            recommendations_used=engagement["recommendations_used"],
            conversion_rate=engagement["conversion_rate"],
        )

        logger.info(
            f"User metrics: Satisfaction={metrics.satisfaction_rate}% (SC-003: {'✓' if metrics.meets_sc003 else '✗'}), "
            f"Completion={metrics.task_completion_rate}% (SC-008: {'✓' if metrics.meets_sc008 else '✗'}), "
            f"Adoption={metrics.adoption_rate}% (SC-012: {'✓' if metrics.meets_sc012 else '✗'})"
        )

        return metrics

    def _calculate_satisfaction(self, cutoff_date: datetime) -> Dict[str, Any]:
        """
        Calculate SC-003: User satisfaction

        Target: 80% of users rate the app 4+ stars (out of 5)

        Args:
            cutoff_date: Start date for analysis

        Returns:
            Satisfaction metrics
        """
        # Get all ratings since cutoff
        ratings = (
            self.db.query(RecommendationFeedback.rating)
            .filter(
                RecommendationFeedback.rating.isnot(None),
                RecommendationFeedback.submitted_at >= cutoff_date,
            )
            .all()
        )

        if not ratings:
            return {
                "avg_rating": 0.0,
                "total_ratings": 0,
                "satisfaction_rate": 0.0,
            }

        ratings_list = [r[0] for r in ratings]
        avg_rating = sum(ratings_list) / len(ratings_list)

        # Count ratings ≥4 (satisfied users)
        satisfied_count = sum(1 for r in ratings_list if r >= 4)
        satisfaction_rate = (satisfied_count / len(ratings_list)) * 100

        return {
            "avg_rating": round(avg_rating, 2),
            "total_ratings": len(ratings_list),
            "satisfaction_rate": round(satisfaction_rate, 2),
        }

    def _calculate_task_completion(self, cutoff_date: datetime) -> float:
        """
        Calculate SC-008: Task completion rate

        Target: 90% of users complete primary workflows

        Primary workflow: Generate recommendation → View → Use/Provide feedback

        Args:
            cutoff_date: Start date for analysis

        Returns:
            Task completion rate (%)
        """
        # Get all recommendations generated (workflow started)
        total_recommendations = (
            self.db.query(func.count(Recommendation.id))
            .filter(Recommendation.created_at >= cutoff_date)
            .scalar()
            or 0
        )

        if total_recommendations == 0:
            return 0.0

        # Count recommendations with feedback (workflow completed)
        completed_workflows = (
            self.db.query(func.count(distinct(RecommendationFeedback.recommendation_id)))
            .join(Recommendation)
            .filter(Recommendation.created_at >= cutoff_date)
            .scalar()
            or 0
        )

        completion_rate = (completed_workflows / total_recommendations) * 100
        return round(completion_rate, 2)

    def _calculate_adoption_rate(self, cutoff_date: datetime) -> Dict[str, Any]:
        """
        Calculate SC-012: Adoption rate

        Target: 60% of vendors with active market presence use recommendations

        "Active market presence" = vendors who have sales data

        Args:
            cutoff_date: Start date for analysis

        Returns:
            Adoption metrics
        """
        # Get all vendors with sales (potential users)
        vendors_with_sales = (
            self.db.query(distinct(Product.vendor_id))
            .filter(Product.created_at >= cutoff_date - timedelta(days=90))  # Active in last 90 days
            .all()
        )

        total_vendors = len(vendors_with_sales)

        if total_vendors == 0:
            return {
                "adoption_rate": 0.0,
                "active_vendors": 0,
                "total_vendors": 0,
            }

        # Get vendors who have generated recommendations (adopters)
        vendors_using_recommendations = (
            self.db.query(distinct(Recommendation.vendor_id))
            .filter(Recommendation.created_at >= cutoff_date)
            .all()
        )

        active_vendors = len(vendors_using_recommendations)
        adoption_rate = (active_vendors / total_vendors) * 100

        return {
            "adoption_rate": round(adoption_rate, 2),
            "active_vendors": active_vendors,
            "total_vendors": total_vendors,
        }

    def _calculate_engagement(self, cutoff_date: datetime) -> Dict[str, Any]:
        """
        Calculate engagement metrics

        Args:
            cutoff_date: Start date for analysis

        Returns:
            Engagement metrics
        """
        recommendations_generated = (
            self.db.query(func.count(Recommendation.id))
            .filter(Recommendation.created_at >= cutoff_date)
            .scalar()
            or 0
        )

        recommendations_used = (
            self.db.query(func.count(distinct(RecommendationFeedback.recommendation_id)))
            .join(Recommendation)
            .filter(Recommendation.created_at >= cutoff_date)
            .scalar()
            or 0
        )

        conversion_rate = (
            (recommendations_used / recommendations_generated) * 100
            if recommendations_generated > 0
            else 0.0
        )

        return {
            "recommendations_generated": recommendations_generated,
            "recommendations_used": recommendations_used,
            "conversion_rate": round(conversion_rate, 2),
        }

    def get_vendor_engagement(
        self,
        vendor_id: str,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get engagement metrics for a specific vendor

        Args:
            vendor_id: Vendor UUID
            days_back: Days of history

        Returns:
            Vendor engagement metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Recommendations generated
        recs_generated = (
            self.db.query(func.count(Recommendation.id))
            .filter(
                Recommendation.vendor_id == vendor_id,
                Recommendation.created_at >= cutoff_date,
            )
            .scalar()
            or 0
        )

        # Feedback provided
        feedback_count = (
            self.db.query(func.count(RecommendationFeedback.id))
            .join(Recommendation)
            .filter(
                Recommendation.vendor_id == vendor_id,
                Recommendation.created_at >= cutoff_date,
            )
            .scalar()
            or 0
        )

        # Average rating
        avg_rating = (
            self.db.query(func.avg(RecommendationFeedback.rating))
            .join(Recommendation)
            .filter(
                Recommendation.vendor_id == vendor_id,
                RecommendationFeedback.rating.isnot(None),
                Recommendation.created_at >= cutoff_date,
            )
            .scalar()
        )

        return {
            "vendor_id": vendor_id,
            "days_analyzed": days_back,
            "recommendations_generated": recs_generated,
            "feedback_provided": feedback_count,
            "feedback_rate": round((feedback_count / recs_generated) * 100, 2) if recs_generated > 0 else 0,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
        }

    def get_feature_usage(
        self,
        days_back: int = 30,
    ) -> Dict[str, int]:
        """
        Get feature usage statistics

        Args:
            days_back: Days of history

        Returns:
            Feature usage counts
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        return {
            "recommendations_generated": (
                self.db.query(func.count(Recommendation.id))
                .filter(Recommendation.created_at >= cutoff_date)
                .scalar()
                or 0
            ),
            "feedback_submitted": (
                self.db.query(func.count(RecommendationFeedback.id))
                .filter(RecommendationFeedback.submitted_at >= cutoff_date)
                .scalar()
                or 0
            ),
            "products_added": (
                self.db.query(func.count(Product.id))
                .filter(Product.created_at >= cutoff_date)
                .scalar()
                or 0
            ),
            "vendors_onboarded": (
                self.db.query(func.count(Vendor.id))
                .filter(Vendor.created_at >= cutoff_date)
                .scalar()
                or 0
            ),
        }


# Scheduled task for metrics collection
def collect_and_log_metrics(db: Session) -> Dict[str, Any]:
    """
    Collect and log user metrics

    Run this as a scheduled task (e.g., daily) to monitor success criteria.

    Args:
        db: Database session

    Returns:
        Metrics collection report
    """
    logger.info("Starting user metrics collection")

    analytics = AnalyticsService(db)

    # Collect metrics
    metrics = analytics.collect_user_metrics(days_back=30)
    feature_usage = analytics.get_feature_usage(days_back=30)

    report = {
        "collected_at": datetime.utcnow().isoformat(),
        "period_days": 30,
        "success_criteria": {
            "sc003_user_satisfaction": {
                "target": f"{AnalyticsService.SC003_TARGET * 100}%",
                "actual": f"{metrics.satisfaction_rate}%",
                "status": "PASS" if metrics.meets_sc003 else "FAIL",
                "avg_rating": metrics.avg_rating,
                "total_ratings": metrics.total_ratings,
            },
            "sc008_task_completion": {
                "target": f"{AnalyticsService.SC008_TARGET * 100}%",
                "actual": f"{metrics.task_completion_rate}%",
                "status": "PASS" if metrics.meets_sc008 else "FAIL",
            },
            "sc012_adoption_rate": {
                "target": f"{AnalyticsService.SC012_TARGET * 100}%",
                "actual": f"{metrics.adoption_rate}%",
                "status": "PASS" if metrics.meets_sc012 else "FAIL",
                "active_vendors": metrics.active_vendors,
                "total_vendors": metrics.total_vendors,
            },
        },
        "engagement": {
            "recommendations_generated": metrics.recommendations_generated,
            "recommendations_used": metrics.recommendations_used,
            "conversion_rate": f"{metrics.conversion_rate}%",
        },
        "feature_usage": feature_usage,
        "overall_health": "HEALTHY" if all([
            metrics.meets_sc003,
            metrics.meets_sc008,
            metrics.meets_sc012,
        ]) else "NEEDS_ATTENTION",
    }

    # Log summary
    logger.info(
        f"Metrics collection complete: "
        f"SC-003: {report['success_criteria']['sc003_user_satisfaction']['status']}, "
        f"SC-008: {report['success_criteria']['sc008_task_completion']['status']}, "
        f"SC-012: {report['success_criteria']['sc012_adoption_rate']['status']}, "
        f"Overall: {report['overall_health']}"
    )

    return report
