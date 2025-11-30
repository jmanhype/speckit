"""Events API routes.

Endpoints:
- POST /events - Create manual event
- GET /events - List events
- DELETE /events/{id} - Delete event
- POST /events/fetch - Fetch from Eventbrite
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.middleware.auth import get_current_vendor
from src.models.event_data import EventData
from src.services.events import EnhancedEventsService


router = APIRouter(prefix="/events", tags=["events"])


class EventCreateRequest(BaseModel):
    """Request to create a manual event."""

    name: str = Field(..., description="Event name")
    event_date: str = Field(..., description="Event date/time (ISO format)")
    location: Optional[str] = Field(None, description="Event location")
    latitude: Optional[float] = Field(None, description="Event latitude")
    longitude: Optional[float] = Field(None, description="Event longitude")
    expected_attendance: int = Field(100, description="Expected attendance")
    is_special: bool = Field(False, description="Whether this is a special/major event")
    description: Optional[str] = Field(None, description="Event description")


class EventResponse(BaseModel):
    """Event response."""

    id: UUID
    name: str
    event_date: str
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    expected_attendance: int
    is_special: bool
    source: str
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class FetchEventsRequest(BaseModel):
    """Request to fetch events from Eventbrite."""

    latitude: float = Field(..., description="Center latitude")
    longitude: float = Field(..., description="Center longitude")
    radius_miles: float = Field(10.0, description="Search radius in miles")
    days_ahead: int = Field(30, description="Number of days to look ahead")


@router.post("", response_model=EventResponse)
def create_event(
    request: EventCreateRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> EventResponse:
    """Create a manual event entry.

    Args:
        request: Event creation parameters
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Created event
    """
    # Parse event date
    try:
        event_date = datetime.fromisoformat(request.event_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
        )

    # Create event
    event = EventData(
        vendor_id=vendor_id,
        name=request.name,
        event_date=event_date,
        location=request.location,
        latitude=request.latitude,
        longitude=request.longitude,
        expected_attendance=request.expected_attendance,
        is_special=request.is_special,
        description=request.description,
        source="manual",
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return EventResponse(
        id=event.id,
        name=event.name,
        event_date=event.event_date.isoformat(),
        location=event.location,
        latitude=float(event.latitude) if event.latitude else None,
        longitude=float(event.longitude) if event.longitude else None,
        expected_attendance=event.expected_attendance,
        is_special=event.is_special,
        source=event.source,
        description=event.description,
        created_at=event.created_at.isoformat(),
    )


@router.get("", response_model=List[EventResponse])
def list_events(
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    days_ahead: int = Query(30, ge=1, le=90),
) -> List[EventResponse]:
    """List upcoming events.

    Args:
        vendor_id: Current vendor ID
        db: Database session
        days_ahead: Number of days to look ahead

    Returns:
        List of events
    """
    today = datetime.utcnow()
    end_date = today + timedelta(days=days_ahead)

    events = (
        db.query(EventData)
        .filter(
            EventData.vendor_id == vendor_id,
            EventData.event_date >= today,
            EventData.event_date <= end_date,
        )
        .order_by(EventData.event_date)
        .all()
    )

    return [
        EventResponse(
            id=event.id,
            name=event.name,
            event_date=event.event_date.isoformat(),
            location=event.location,
            latitude=float(event.latitude) if event.latitude else None,
            longitude=float(event.longitude) if event.longitude else None,
            expected_attendance=event.expected_attendance,
            is_special=event.is_special,
            source=event.source,
            description=event.description,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]


@router.delete("/{event_id}")
def delete_event(
    event_id: UUID,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Delete an event.

    Args:
        event_id: Event UUID
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Success message
    """
    event = (
        db.query(EventData)
        .filter(
            EventData.id == event_id,
            EventData.vendor_id == vendor_id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    db.delete(event)
    db.commit()

    return {"message": "Event deleted successfully"}


@router.post("/fetch")
async def fetch_eventbrite_events(
    request: FetchEventsRequest,
    vendor_id: UUID = Depends(get_current_vendor),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch events from Eventbrite API with graceful degradation.

    Continues operation even if Eventbrite API is unavailable.
    System can still use database events and hardcoded dates.

    Args:
        request: Fetch parameters
        vendor_id: Current vendor ID
        db: Database session

    Returns:
        Fetch statistics and status
    """
    # Initialize enhanced events service
    events_service = EnhancedEventsService(vendor_id=vendor_id, db=db)

    # Fetch events
    today = datetime.utcnow()
    end_date = today + timedelta(days=request.days_ahead)

    stats = await events_service.fetch_eventbrite_events(
        lat=request.latitude,
        lon=request.longitude,
        start_date=today,
        end_date=end_date,
        radius_miles=request.radius_miles,
    )

    # Build response message
    if stats.get("degraded"):
        message = (
            "Eventbrite API unavailable - "
            "continuing with database and hardcoded events"
        )
    else:
        new_count = stats.get("new", 0)
        message = f"Successfully fetched {new_count} new events from Eventbrite"

    return {
        "message": message,
        **stats,  # Include all stats
    }
