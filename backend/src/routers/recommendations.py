"""Recommendations API routes.

Endpoints:
- POST /recommendations/generate - Generate recommendations
- GET /recommendations - List recommendations
- GET /recommendations/{id} - Get recommendation details
- PUT /recommendations/{id}/feedback - Update user feedback
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.recommendation import Recommendation
from src.models.product import Product
from src.models.venue import Venue
from src.services.ml_recommendations import MLRecommendationService
from src.services.weather import weather_service
from src.services.events import events_service


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class GenerateRequest(BaseModel):
    """Request to generate recommendations."""

    market_date: str = Field(..., description="Market date (ISO format)")
    latitude: Optional[float] = Field(None, description="Market location latitude")
    longitude: Optional[float] = Field(None, description="Market location longitude")
    venue_id: Optional[UUID] = Field(None, description="Venue UUID (optional)")


class ProductInfo(BaseModel):
    """Product information for recommendation."""

    id: UUID
    name: str
    price: float
    category: Optional[str]


class WeatherData(BaseModel):
    """Weather data for recommendation."""

    condition: Optional[str] = None
    temp_f: Optional[float] = None
    feels_like_f: Optional[float] = None
    humidity: Optional[float] = None
    description: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Recommendation response."""

    id: UUID
    market_date: str
    product: ProductInfo
    recommended_quantity: int
    confidence_score: float
    predicted_revenue: Optional[float]
    weather_condition: Optional[str]  # Deprecated - use weather_data
    weather_data: Optional[WeatherData] = None
    is_special_event: bool
    generated_at: str
    venue_id: Optional[UUID] = None  # Venue UUID if venue-specific
    venue_name: Optional[str] = None  # Venue name for display
    is_seasonal: Optional[bool] = None  # Whether product is seasonal
    confidence_level: str = "medium"  # Confidence level: low/medium/high

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    """User feedback on recommendation."""

    accepted: bool
    actual_quantity: Optional[int] = None


@router.post("/generate")
async def generate_recommendations(
    request: GenerateRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Generate AI recommendations for market date.

    Args:
        request: Generation parameters
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Generation status and count
    """
    # Parse market date
    try:
        market_date = datetime.fromisoformat(request.market_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid market_date format. Use ISO format (YYYY-MM-DD)",
        )

    # Fetch weather forecast if location provided
    weather_data = None
    if request.latitude and request.longitude:
        weather_data = await weather_service.get_forecast(
            lat=request.latitude,
            lon=request.longitude,
            target_date=market_date,
        )

    # Get event information
    event_data = events_service.get_event_for_date(market_date)

    # Initialize ML service
    ml_service = MLRecommendationService(vendor_id=vendor_id, db=db)

    # Generate recommendations for all active products
    recommendations = ml_service.generate_recommendations_for_date(
        market_date=market_date,
        weather_data=weather_data,
        event_data=event_data,
        venue_id=request.venue_id,  # Pass venue_id to ML service
        limit=20,
    )

    # Save recommendations to database
    for rec in recommendations:
        db.add(rec)

    db.commit()

    return {
        "message": "Recommendations generated successfully",
        "count": len(recommendations),
        "market_date": market_date.isoformat(),
    }


@router.get("", response_model=List[RecommendationResponse])
def list_recommendations(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    market_date: Optional[str] = Query(None),
    days_ahead: int = Query(7, ge=1, le=30),
    limit: int = Query(20, le=100),
) -> List[RecommendationResponse]:
    """List recommendations for vendor.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        market_date: Filter by specific market date
        days_ahead: Show recommendations for next N days
        limit: Maximum recommendations to return

    Returns:
        List of recommendations with product details
    """
    query = db.query(Recommendation).filter(Recommendation.vendor_id == vendor_id)

    if market_date:
        # Filter by specific date
        try:
            target_date = datetime.fromisoformat(market_date)
            query = query.filter(Recommendation.market_date == target_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid market_date format",
            )
    else:
        # Filter by date range
        today = datetime.utcnow().date()
        end_date = today + timedelta(days=days_ahead)

        query = query.filter(
            Recommendation.market_date >= today,
            Recommendation.market_date <= end_date,
        )

    recommendations = (
        query.order_by(Recommendation.market_date, Recommendation.confidence_score.desc())
        .limit(limit)
        .all()
    )

    # Build response with product details
    result = []
    for rec in recommendations:
        product = db.query(Product).filter(Product.id == rec.product_id).first()

        if not product:
            continue

        # Extract weather data
        weather_data = None
        if rec.weather_features:
            weather_data = WeatherData(
                condition=rec.weather_features.get("condition"),
                temp_f=rec.weather_features.get("temp_f"),
                feels_like_f=rec.weather_features.get("feels_like_f"),
                humidity=rec.weather_features.get("humidity"),
                description=rec.weather_features.get("description"),
            )

        # Get venue information if present
        venue_name = None
        if rec.venue_id:
            venue = db.query(Venue).filter(Venue.id == rec.venue_id).first()
            if venue:
                venue_name = venue.name

        # Extract seasonal information
        is_seasonal = None
        if rec.historical_features:
            is_seasonal = bool(rec.historical_features.get("is_seasonal", 0))

        # Determine confidence level category
        confidence_value = float(rec.confidence_score)
        if confidence_value >= 0.7:
            confidence_level = "high"
        elif confidence_value >= 0.5:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        result.append(
            RecommendationResponse(
                id=rec.id,
                market_date=rec.market_date.isoformat(),
                product=ProductInfo(
                    id=product.id,
                    name=product.name,
                    price=float(product.price),
                    category=product.category,
                ),
                recommended_quantity=rec.recommended_quantity,
                confidence_score=confidence_value,
                predicted_revenue=float(rec.predicted_revenue)
                if rec.predicted_revenue
                else None,
                weather_condition=rec.weather_features.get("condition")
                if rec.weather_features
                else None,
                weather_data=weather_data,
                is_special_event=rec.event_features.get("is_special", False)
                if rec.event_features
                else False,
                generated_at=rec.generated_at.isoformat(),
                venue_id=rec.venue_id,
                venue_name=venue_name,
                is_seasonal=is_seasonal,
                confidence_level=confidence_level,
            )
        )

    return result


@router.put("/{recommendation_id}/feedback")
def update_feedback(
    recommendation_id: UUID,
    feedback: FeedbackRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Update user feedback on recommendation.

    Args:
        recommendation_id: Recommendation UUID
        feedback: User feedback
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Success message
    """
    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == recommendation_id,
            Recommendation.vendor_id == vendor_id,
        )
        .first()
    )

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    # Update feedback
    recommendation.user_accepted = feedback.accepted
    if feedback.actual_quantity is not None:
        recommendation.actual_quantity_brought = feedback.actual_quantity

    db.commit()

    return {"message": "Feedback updated successfully"}
