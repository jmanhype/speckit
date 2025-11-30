"""EventData model for storing local events.

Events can be manually entered by vendors or automatically fetched from APIs.
Used to adjust predictions based on expected attendance impact.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Numeric, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantModel


class EventData(TenantModel):
    """
    EventData represents a local event that may affect market sales.

    Events can be:
    - Manually entered by vendors
    - Fetched from Eventbrite API
    - Hardcoded special dates (holidays)
    """

    __tablename__ = "event_data"

    # Event Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Event name",
    )

    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Date/time of event",
    )

    location: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Event location/venue",
    )

    # Geolocation (for radius search)
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Event latitude",
    )

    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Event longitude",
    )

    # Impact metrics
    expected_attendance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="Expected number of attendees",
    )

    is_special: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Whether this is a special/major event",
    )

    # Event source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Source of event data (manual, eventbrite, hardcoded)",
    )

    # Optional details
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Event description",
    )

    eventbrite_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Eventbrite event ID (if from API)",
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_event_data_vendor_date', 'vendor_id', 'event_date'),
        Index('ix_event_data_location', 'latitude', 'longitude'),
        Index('ix_event_data_date_range', 'event_date'),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<EventData(id={self.id}, vendor_id={self.vendor_id}, "
            f"name='{self.name}', event_date={self.event_date}, "
            f"attendance={self.expected_attendance})>"
        )
