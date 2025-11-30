"""RecommendationFeedback model for tracking recommendation accuracy.

Allows vendors to provide feedback on recommendations:
- Actual quantity sold vs recommended
- Rating (1-5 stars)
- Comments
- Variance tracking for ML model improvement
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Numeric, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TenantModel


class RecommendationFeedback(TenantModel):
    """Feedback on recommendation accuracy from vendors.

    Tracks actual outcomes vs predictions for ML model improvement.
    """

    __tablename__ = "recommendation_feedback"

    # Foreign key to recommendation
    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Actual quantity brought to market
    actual_quantity_brought: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual quantity vendor brought to market",
    )

    # Actual quantity sold
    actual_quantity_sold: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual quantity sold at market",
    )

    # Actual revenue
    actual_revenue: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Actual revenue from sales",
    )

    # Variance metrics (calculated)
    quantity_variance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Variance between recommended and actual sold (actual - recommended)",
    )

    variance_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Variance as percentage",
    )

    # Vendor rating (1-5 stars)
    rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Vendor rating of recommendation accuracy (1-5)",
    )

    # Vendor comments
    comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Vendor feedback comments",
    )

    # Outcome flags
    was_accurate: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether recommendation was within acceptable range (±20%)",
    )

    was_overstocked: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether vendor brought too much inventory",
    )

    was_understocked: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether vendor ran out of stock",
    )

    # Submission timestamp
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When feedback was submitted",
    )

    # Relationship to recommendation
    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation",
        back_populates="feedback",
    )

    __table_args__ = (
        # Index for analytics queries
        Index("idx_feedback_vendor_submitted", "vendor_id", "submitted_at"),
        Index("idx_feedback_accuracy", "was_accurate"),
        Index("idx_feedback_rating", "rating"),
    )

    def __repr__(self):
        return (
            f"<RecommendationFeedback("
            f"id={self.id}, "
            f"recommendation_id={self.recommendation_id}, "
            f"rating={self.rating}, "
            f"variance={self.variance_percentage}%"
            f")>"
        )

    def calculate_variance(self, recommended_quantity: int) -> None:
        """Calculate variance metrics from actual vs recommended.

        Args:
            recommended_quantity: The original recommended quantity
        """
        if self.actual_quantity_sold is None:
            return

        # Quantity variance (positive = sold more than recommended)
        self.quantity_variance = Decimal(self.actual_quantity_sold - recommended_quantity)

        # Variance percentage
        if recommended_quantity > 0:
            self.variance_percentage = (
                Decimal(self.actual_quantity_sold - recommended_quantity)
                / Decimal(recommended_quantity)
                * 100
            )
        else:
            self.variance_percentage = Decimal(0)

        # Determine accuracy (within ±20%)
        self.was_accurate = abs(float(self.variance_percentage)) <= 20.0

        # Determine overstock/understock
        self.was_overstocked = float(self.variance_percentage) < -20.0
        self.was_understocked = float(self.variance_percentage) > 20.0
