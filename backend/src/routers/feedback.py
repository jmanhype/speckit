"""Recommendation feedback API routes.

Endpoints:
- POST /feedback - Submit feedback for a recommendation
- GET /feedback - List feedback entries
- GET /feedback/stats - Get feedback statistics
- GET /feedback/{id} - Get specific feedback
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback


router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreateRequest(BaseModel):
    """Request to create feedback for a recommendation."""

    recommendation_id: UUID = Field(..., description="Recommendation UUID")
    actual_quantity_brought: Optional[int] = Field(None, description="Actual quantity brought to market")
    actual_quantity_sold: Optional[int] = Field(None, description="Actual quantity sold")
    actual_revenue: Optional[float] = Field(None, description="Actual revenue in USD")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5 stars")
    comments: Optional[str] = Field(None, description="Vendor comments")


class FeedbackResponse(BaseModel):
    """Feedback response."""

    id: UUID
    recommendation_id: UUID
    actual_quantity_brought: Optional[int]
    actual_quantity_sold: Optional[int]
    actual_revenue: Optional[float]
    quantity_variance: Optional[float]
    variance_percentage: Optional[float]
    rating: Optional[int]
    comments: Optional[str]
    was_accurate: Optional[bool]
    was_overstocked: Optional[bool]
    was_understocked: Optional[bool]
    submitted_at: str

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """Feedback statistics."""

    total_feedback_count: int
    avg_rating: Optional[float]
    accuracy_rate: Optional[float]  # Percentage within ±20%
    overstock_rate: Optional[float]  # Percentage overstocked
    understock_rate: Optional[float]  # Percentage understocked
    avg_variance_percentage: Optional[float]


@router.post("", response_model=FeedbackResponse)
def create_feedback(
    request: FeedbackCreateRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """Submit feedback for a recommendation.

    Args:
        request: Feedback data
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Created feedback

    Raises:
        404: Recommendation not found
        409: Feedback already exists for this recommendation
    """
    # Verify recommendation exists and belongs to vendor
    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == request.recommendation_id,
            Recommendation.vendor_id == vendor_id,
        )
        .first()
    )

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    # Check if feedback already exists
    existing_feedback = (
        db.query(RecommendationFeedback)
        .filter(
            RecommendationFeedback.recommendation_id == request.recommendation_id,
            RecommendationFeedback.vendor_id == vendor_id,
        )
        .first()
    )

    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists for this recommendation",
        )

    # Create feedback
    feedback = RecommendationFeedback(
        vendor_id=vendor_id,
        recommendation_id=request.recommendation_id,
        actual_quantity_brought=request.actual_quantity_brought,
        actual_quantity_sold=request.actual_quantity_sold,
        actual_revenue=request.actual_revenue,
        rating=request.rating,
        comments=request.comments,
    )

    # Calculate variance if actual_quantity_sold is provided
    if request.actual_quantity_sold is not None:
        feedback.calculate_variance(recommendation.recommended_quantity)

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        recommendation_id=feedback.recommendation_id,
        actual_quantity_brought=feedback.actual_quantity_brought,
        actual_quantity_sold=feedback.actual_quantity_sold,
        actual_revenue=float(feedback.actual_revenue) if feedback.actual_revenue else None,
        quantity_variance=float(feedback.quantity_variance) if feedback.quantity_variance else None,
        variance_percentage=float(feedback.variance_percentage) if feedback.variance_percentage else None,
        rating=feedback.rating,
        comments=feedback.comments,
        was_accurate=feedback.was_accurate,
        was_overstocked=feedback.was_overstocked,
        was_understocked=feedback.was_understocked,
        submitted_at=feedback.submitted_at.isoformat(),
    )


@router.get("", response_model=List[FeedbackResponse])
def list_feedback(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[FeedbackResponse]:
    """List feedback entries.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        limit: Maximum number of entries
        offset: Offset for pagination

    Returns:
        List of feedback entries
    """
    feedback_list = (
        db.query(RecommendationFeedback)
        .filter(RecommendationFeedback.vendor_id == vendor_id)
        .order_by(RecommendationFeedback.submitted_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        FeedbackResponse(
            id=f.id,
            recommendation_id=f.recommendation_id,
            actual_quantity_brought=f.actual_quantity_brought,
            actual_quantity_sold=f.actual_quantity_sold,
            actual_revenue=float(f.actual_revenue) if f.actual_revenue else None,
            quantity_variance=float(f.quantity_variance) if f.quantity_variance else None,
            variance_percentage=float(f.variance_percentage) if f.variance_percentage else None,
            rating=f.rating,
            comments=f.comments,
            was_accurate=f.was_accurate,
            was_overstocked=f.was_overstocked,
            was_understocked=f.was_understocked,
            submitted_at=f.submitted_at.isoformat(),
        )
        for f in feedback_list
    ]


@router.get("/stats", response_model=FeedbackStats)
def get_feedback_stats(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days_back: int = Query(30, ge=1, le=365),
) -> FeedbackStats:
    """Get feedback statistics.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        days_back: Number of days to include

    Returns:
        Feedback statistics
    """
    # Calculate date range
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    # Get all feedback in range
    feedback_list = (
        db.query(RecommendationFeedback)
        .filter(
            RecommendationFeedback.vendor_id == vendor_id,
            RecommendationFeedback.submitted_at >= cutoff_date,
        )
        .all()
    )

    total_count = len(feedback_list)

    if total_count == 0:
        return FeedbackStats(
            total_feedback_count=0,
            avg_rating=None,
            accuracy_rate=None,
            overstock_rate=None,
            understock_rate=None,
            avg_variance_percentage=None,
        )

    # Calculate statistics
    ratings = [f.rating for f in feedback_list if f.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else None

    accurate_count = sum(1 for f in feedback_list if f.was_accurate is True)
    accuracy_rate = (accurate_count / total_count) * 100 if total_count > 0 else None

    overstock_count = sum(1 for f in feedback_list if f.was_overstocked is True)
    overstock_rate = (overstock_count / total_count) * 100 if total_count > 0 else None

    understock_count = sum(1 for f in feedback_list if f.was_understocked is True)
    understock_rate = (understock_count / total_count) * 100 if total_count > 0 else None

    variances = [
        float(f.variance_percentage)
        for f in feedback_list
        if f.variance_percentage is not None
    ]
    avg_variance = sum(variances) / len(variances) if variances else None

    return FeedbackStats(
        total_feedback_count=total_count,
        avg_rating=round(avg_rating, 2) if avg_rating else None,
        accuracy_rate=round(accuracy_rate, 2) if accuracy_rate else None,
        overstock_rate=round(overstock_rate, 2) if overstock_rate else None,
        understock_rate=round(understock_rate, 2) if understock_rate else None,
        avg_variance_percentage=round(avg_variance, 2) if avg_variance else None,
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
def get_feedback(
    feedback_id: UUID,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """Get specific feedback entry.

    Args:
        feedback_id: Feedback UUID
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Feedback entry

    Raises:
        404: Feedback not found
    """
    feedback = (
        db.query(RecommendationFeedback)
        .filter(
            RecommendationFeedback.id == feedback_id,
            RecommendationFeedback.vendor_id == vendor_id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    return FeedbackResponse(
        id=feedback.id,
        recommendation_id=feedback.recommendation_id,
        actual_quantity_brought=feedback.actual_quantity_brought,
        actual_quantity_sold=feedback.actual_quantity_sold,
        actual_revenue=float(feedback.actual_revenue) if feedback.actual_revenue else None,
        quantity_variance=float(feedback.quantity_variance) if feedback.quantity_variance else None,
        variance_percentage=float(feedback.variance_percentage) if feedback.variance_percentage else None,
        rating=feedback.rating,
        comments=feedback.comments,
        was_accurate=feedback.was_accurate,
        was_overstocked=feedback.was_overstocked,
        was_understocked=feedback.was_understocked,
        submitted_at=feedback.submitted_at.isoformat(),
    )
