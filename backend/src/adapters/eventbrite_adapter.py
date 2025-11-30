"""Eventbrite API adapter for fetching local events.

Integrates with Eventbrite API to automatically discover events
near market venues that may impact sales.

Features graceful degradation:
- Returns empty list on API failure (doesn't crash)
- Logs detailed error information
- Continues operation when API is unavailable
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import httpx

from src.config import settings


logger = logging.getLogger(__name__)


class EventbriteAPIError(Exception):
    """Exception raised when Eventbrite API is unavailable."""
    pass


class EventbriteAdapter:
    """Adapter for Eventbrite API integration."""

    BASE_URL = "https://www.eventbriteapi.com/v3"
    SPECIAL_EVENT_THRESHOLD = 1000  # Events >1000 capacity are "special"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Eventbrite adapter.

        Args:
            api_key: Eventbrite OAuth token (optional, falls back to settings)
        """
        self.api_key = api_key or getattr(settings, 'eventbrite_api_key', None)

    async def search_events(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Search for events near a location and date range with graceful degradation.

        Returns empty list on any failure, allowing system to continue
        with database events and hardcoded dates.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_miles: Search radius in miles
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of event dictionaries (empty on failure)
        """
        if not self.api_key:
            logger.warning(
                "Eventbrite API key not configured - "
                "continuing with database/hardcoded events only"
            )
            return []

        try:
            async with httpx.AsyncClient() as client:
                # Convert miles to kilometers for API
                radius_km = radius_miles * 1.60934

                # Format dates for API (ISO 8601)
                start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
                end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")

                # Build API request
                url = f"{self.BASE_URL}/events/search/"
                params = {
                    "location.latitude": latitude,
                    "location.longitude": longitude,
                    "location.within": f"{radius_km}km",
                    "start_date.range_start": start_str,
                    "start_date.range_end": end_str,
                    "expand": "venue",
                }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }

                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"Eventbrite API returned status {response.status_code} - "
                        f"continuing with database/hardcoded events only"
                    )
                    return []

                data = response.json()

                # Parse events
                events = []
                for event_data in data.get("events", []):
                    parsed_event = self._parse_event(event_data)
                    if parsed_event:
                        events.append(parsed_event)

                logger.info(f"Found {len(events)} events from Eventbrite near ({latitude}, {longitude})")
                return events

        except httpx.TimeoutException as e:
            logger.warning(
                f"Eventbrite API timeout after 10s - "
                f"continuing with database/hardcoded events only"
            )
            return []
        except httpx.HTTPError as e:
            logger.warning(
                f"Eventbrite API HTTP error: {e} - "
                f"continuing with database/hardcoded events only"
            )
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error fetching from Eventbrite: {e} - "
                f"continuing with database/hardcoded events only",
                exc_info=True
            )
            return []

    def _parse_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Eventbrite event data into our format.

        Args:
            event_data: Raw event data from Eventbrite API

        Returns:
            Parsed event dictionary or None
        """
        try:
            # Extract basic info
            name = event_data.get("name", {}).get("text", "Unknown Event")
            description = event_data.get("description", {}).get("text", "")

            # Parse event date
            start_str = event_data.get("start", {}).get("local")
            if not start_str:
                return None

            event_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

            # Extract venue/location
            venue = event_data.get("venue", {})
            location = venue.get("name", "")

            address = venue.get("address", {})
            lat_str = address.get("latitude")
            lon_str = address.get("longitude")

            latitude = Decimal(lat_str) if lat_str else None
            longitude = Decimal(lon_str) if lon_str else None

            # Estimate attendance from capacity
            capacity = event_data.get("capacity")
            expected_attendance = int(capacity) if capacity else 500

            # Mark large events as special
            is_special = expected_attendance >= self.SPECIAL_EVENT_THRESHOLD

            # Get Eventbrite ID
            eventbrite_id = event_data.get("id")

            return {
                "name": name,
                "event_date": event_date,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "expected_attendance": expected_attendance,
                "is_special": is_special,
                "description": description[:500] if description else "",  # Truncate
                "eventbrite_id": eventbrite_id,
                "source": "eventbrite",
            }

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None
