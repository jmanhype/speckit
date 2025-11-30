"""Venue model for market locations.

Venues represent physical locations where vendors sell (farmers markets, events, etc.).
Used for venue-specific predictions and performance tracking.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Numeric, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantModel


class Venue(TenantModel):
    """
    Venue represents a market location.

    Used for:
    - Venue-specific ML predictions
    - Performance tracking per location
    - Location-based analytics
    """

    __tablename__ = "venues"

    # Venue Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Market or venue name",
    )

    location: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Address or location description",
    )

    # Geolocation (for weather/events)
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Latitude coordinate",
    )

    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Longitude coordinate",
    )

    # Venue Characteristics
    typical_attendance: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Typical number of customers",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Vendor notes about this venue",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default='true',
        comment="Whether vendor still attends this venue",
    )

    # Indexes for queries
    __table_args__ = (
        Index('ix_venues_vendor_active', 'vendor_id', 'is_active'),
        Index('ix_venues_name', 'name'),
        Index('ix_venues_location_coords', 'latitude', 'longitude'),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Venue(id={self.id}, vendor_id={self.vendor_id}, "
            f"name='{self.name}', location='{self.location}')>"
        )
