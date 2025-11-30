"""Events service for market event information.

Enhanced service with database storage, Eventbrite API integration,
and radius search for local events.

Features graceful degradation:
- Falls back to database events if Eventbrite API fails
- Falls back to hardcoded dates if no database events
- Continues operations even when external API is unavailable
- Logs warnings but doesn't crash
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from src.models.event_data import EventData
from src.adapters.eventbrite_adapter import EventbriteAdapter, EventbriteAPIError


logger = logging.getLogger(__name__)


class EventsService:
    """Basic service for detecting special market events (backward compatible)."""

    # Known special event days (fallback)
    SPECIAL_DATES = {
        # Holiday markets (more traffic)
        "2025-12-25": {"name": "Christmas Market", "attendance_multiplier": 2.0},
        "2025-07-04": {"name": "4th of July Market", "attendance_multiplier": 1.8},
        "2025-11-28": {"name": "Thanksgiving Market", "attendance_multiplier": 1.5},
    }

    def get_event_for_date(self, target_date: datetime) -> Optional[Dict[str, Any]]:
        """Get event information for a date.

        Args:
            target_date: Target market date

        Returns:
            Event data dictionary or None
        """
        date_key = target_date.strftime("%Y-%m-%d")

        if date_key in self.SPECIAL_DATES:
            event_info = self.SPECIAL_DATES[date_key]

            return {
                "name": event_info["name"],
                "expected_attendance": 200 * event_info["attendance_multiplier"],
                "is_special": True,
            }

        # Check for weekend markets (typically higher traffic)
        if target_date.weekday() in [5, 6]:  # Saturday or Sunday
            return {
                "name": "Weekend Market",
                "expected_attendance": 150,
                "is_special": False,
            }

        # Weekday market (lower traffic)
        return {
            "name": "Weekday Market",
            "expected_attendance": 100,
            "is_special": False,
        }


class EnhancedEventsService:
    """Enhanced events service with database and API integration."""

    # Default search radius (miles)
    DEFAULT_RADIUS_MILES = 10.0

    # Threshold for high-impact events
    HIGH_IMPACT_THRESHOLD = 1000

    def __init__(self, vendor_id: UUID, db: Session):
        """Initialize enhanced events service.

        Args:
            vendor_id: Vendor UUID
            db: Database session
        """
        self.vendor_id = vendor_id
        self.db = db
        self.eventbrite = EventbriteAdapter()
        self.fallback_service = EventsService()  # Fallback to basic service

    def get_event_for_date(self, target_date: datetime) -> Optional[Dict[str, Any]]:
        """Get event for a specific date.

        Checks database first, then falls back to hardcoded dates.

        Args:
            target_date: Target market date

        Returns:
            Event data dictionary
        """
        # Check database for manual or fetched events
        db_event = self._get_database_event(target_date)
        if db_event:
            return db_event

        # Fallback to hardcoded special dates
        return self.fallback_service.get_event_for_date(target_date)

    def find_events_near_location(
        self,
        lat: float,
        lon: float,
        target_date: datetime,
        radius_miles: float = None,
    ) -> Optional[Dict[str, Any]]:
        """Find events near a location for a specific date.

        Args:
            lat: Latitude
            lon: Longitude
            target_date: Target date
            radius_miles: Search radius in miles (default: 10)

        Returns:
            Largest event within radius, or None
        """
        if radius_miles is None:
            radius_miles = self.DEFAULT_RADIUS_MILES

        # Query database for events on that date
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        events = (
            self.db.query(EventData)
            .filter(
                EventData.vendor_id == self.vendor_id,
                EventData.event_date >= start_of_day,
                EventData.event_date < end_of_day,
                EventData.latitude.isnot(None),
                EventData.longitude.isnot(None),
            )
            .all()
        )

        # Filter by radius and find largest
        nearby_events = []
        for event in events:
            distance = self._calculate_distance(
                lat, lon,
                float(event.latitude), float(event.longitude)
            )

            if distance <= radius_miles:
                nearby_events.append(event)

        if not nearby_events:
            return None

        # Return event with highest attendance
        largest_event = max(nearby_events, key=lambda e: e.expected_attendance)

        return {
            "name": largest_event.name,
            "expected_attendance": largest_event.expected_attendance,
            "is_special": largest_event.is_special,
            "location": largest_event.location,
        }

    def calculate_attendance_impact(self, event_data: Dict[str, Any]) -> float:
        """Calculate attendance multiplier for an event.

        Args:
            event_data: Event information

        Returns:
            Attendance multiplier (1.0 = no impact, >1.0 = higher attendance)
        """
        attendance = event_data.get("expected_attendance", 100)
        is_special = event_data.get("is_special", False)

        # Base multiplier
        if is_special:
            base_multiplier = 1.5
        else:
            base_multiplier = 1.0

        # Scale by attendance
        if attendance >= 5000:
            return base_multiplier * 2.0
        elif attendance >= 2000:
            return base_multiplier * 1.5
        elif attendance >= 1000:
            return base_multiplier * 1.3
        elif attendance >= 500:
            return base_multiplier * 1.2
        else:
            return base_multiplier * 1.1

    async def fetch_eventbrite_events(
        self,
        lat: float,
        lon: float,
        start_date: datetime,
        end_date: datetime,
        radius_miles: float = None,
    ) -> Dict[str, Any]:
        """Fetch events from Eventbrite and store in database with graceful degradation.

        Continues operation even if Eventbrite API is unavailable.
        System can still use database events and hardcoded dates.

        Args:
            lat: Latitude
            lon: Longitude
            start_date: Start of date range
            end_date: End of date range
            radius_miles: Search radius

        Returns:
            Dictionary with fetch statistics and status
        """
        if radius_miles is None:
            radius_miles = self.DEFAULT_RADIUS_MILES

        try:
            # Fetch from Eventbrite (returns empty list on failure)
            events = await self.eventbrite.search_events(
                latitude=lat,
                longitude=lon,
                radius_miles=radius_miles,
                start_date=start_date,
                end_date=end_date,
            )

            # Check if Eventbrite returned events
            if not events:
                logger.warning(
                    "No events returned from Eventbrite - "
                    "using database and hardcoded events for recommendations"
                )
                return {
                    "fetched": 0,
                    "new": 0,
                    "duplicates": 0,
                    "api_available": False,
                    "degraded": True,
                }

            # Store in database
            new_count = 0
            duplicate_count = 0

            for event_data in events:
                try:
                    # Check if event already exists
                    existing = (
                        self.db.query(EventData)
                        .filter(
                            EventData.vendor_id == self.vendor_id,
                            EventData.eventbrite_id == event_data["eventbrite_id"],
                        )
                        .first()
                    )

                    if not existing:
                        event = EventData(
                            vendor_id=self.vendor_id,
                            **event_data
                        )
                        self.db.add(event)
                        new_count += 1
                    else:
                        duplicate_count += 1

                except Exception as e:
                    logger.warning(f"Failed to store event {event_data.get('name')}: {e}")
                    continue

            self.db.commit()
            logger.info(f"Fetched {new_count} new events from Eventbrite ({duplicate_count} duplicates skipped)")

            return {
                "fetched": len(events),
                "new": new_count,
                "duplicates": duplicate_count,
                "api_available": True,
                "degraded": False,
            }

        except Exception as e:
            logger.error(
                f"Unexpected error in fetch_eventbrite_events: {e} - "
                f"continuing with database and hardcoded events",
                exc_info=True
            )
            return {
                "fetched": 0,
                "new": 0,
                "duplicates": 0,
                "api_available": False,
                "degraded": True,
                "error": str(e),
            }

    def _get_database_event(self, target_date: datetime) -> Optional[Dict[str, Any]]:
        """Get event from database for a date.

        Args:
            target_date: Target date

        Returns:
            Event dictionary or None
        """
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Find events on this date
        events = (
            self.db.query(EventData)
            .filter(
                EventData.vendor_id == self.vendor_id,
                EventData.event_date >= start_of_day,
                EventData.event_date < end_of_day,
            )
            .all()
        )

        if not events:
            return None

        # Return largest event if multiple
        largest = max(events, key=lambda e: e.expected_attendance)

        return {
            "name": largest.name,
            "expected_attendance": largest.expected_attendance,
            "is_special": largest.is_special,
            "location": largest.location,
        }

    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two points using Haversine formula.

        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2

        Returns:
            Distance in miles
        """
        # Earth radius in miles
        R = 3959.0

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance


# Global events service instance (backward compatible)
events_service = EventsService()
