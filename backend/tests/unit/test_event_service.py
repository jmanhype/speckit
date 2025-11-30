"""Unit tests for event service.

Tests event detection and radius search for local events.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.services.events import EnhancedEventsService


class TestEnhancedEventsService:
    """Test enhanced events service with database and API integration."""

    @pytest.fixture
    def vendor_id(self):
        """Test vendor ID."""
        return uuid4()

    @pytest.fixture
    def events_service(self, db_session, vendor_id):
        """Create events service."""
        return EnhancedEventsService(vendor_id=vendor_id, db=db_session)

    def test_get_event_for_date_from_database(self, events_service, db_session, vendor_id):
        """Test retrieving manually entered event from database."""
        # This test will fail until EventData model is created
        from src.models.event_data import EventData

        # Create manual event
        event_date = datetime(2025, 6, 15, 10, 0)
        event = EventData(
            vendor_id=vendor_id,
            name="Farmer's Market Festival",
            event_date=event_date,
            location="Downtown Plaza",
            expected_attendance=500,
            is_special=True,
            source="manual",
        )
        db_session.add(event)
        db_session.commit()

        # Retrieve event
        result = events_service.get_event_for_date(event_date)

        assert result is not None
        assert result["name"] == "Farmer's Market Festival"
        assert result["expected_attendance"] == 500
        assert result["is_special"] is True

    def test_radius_search_finds_nearby_events(self, events_service, db_session, vendor_id):
        """Test finding events within radius of venue."""
        from src.models.event_data import EventData

        event_date = datetime(2025, 6, 15, 10, 0)

        # Create event near venue (within 5 miles)
        nearby_event = EventData(
            vendor_id=vendor_id,
            name="Music Festival",
            event_date=event_date,
            location="City Park",
            latitude=Decimal("37.7849"),  # ~0.7 miles from venue
            longitude=Decimal("-122.4294"),
            expected_attendance=1000,
            is_special=True,
            source="eventbrite",
        )
        db_session.add(nearby_event)
        db_session.commit()

        # Search for events near venue
        venue_lat = 37.7749
        venue_lon = -122.4194

        result = events_service.find_events_near_location(
            lat=venue_lat,
            lon=venue_lon,
            target_date=event_date,
            radius_miles=5.0,
        )

        assert result is not None
        assert result["name"] == "Music Festival"
        assert result["expected_attendance"] == 1000

    def test_radius_search_excludes_far_events(self, events_service, db_session, vendor_id):
        """Test that events outside radius are excluded."""
        from src.models.event_data import EventData

        event_date = datetime(2025, 6, 15, 10, 0)

        # Create event far from venue (>10 miles)
        far_event = EventData(
            vendor_id=vendor_id,
            name="Far Away Festival",
            event_date=event_date,
            location="Distant Town",
            latitude=Decimal("37.9000"),  # ~10 miles away
            longitude=Decimal("-122.5000"),
            expected_attendance=2000,
            is_special=True,
            source="eventbrite",
        )
        db_session.add(far_event)
        db_session.commit()

        # Search with small radius
        result = events_service.find_events_near_location(
            lat=37.7749,
            lon=-122.4194,
            target_date=event_date,
            radius_miles=5.0,
        )

        # Should not find the far event
        assert result is None or result["name"] != "Far Away Festival"

    def test_event_impact_on_attendance(self, events_service):
        """Test calculating attendance multiplier for events."""
        # High-impact event
        high_impact = {
            "expected_attendance": 2000,
            "is_special": True,
        }

        multiplier_high = events_service.calculate_attendance_impact(high_impact)
        assert multiplier_high > 1.5

        # Low-impact event
        low_impact = {
            "expected_attendance": 100,
            "is_special": False,
        }

        multiplier_low = events_service.calculate_attendance_impact(low_impact)
        assert multiplier_low <= 1.2

    def test_fallback_to_hardcoded_events(self, events_service):
        """Test fallback to hardcoded events when no database events exist."""
        # Christmas should be detected even without database
        christmas = datetime(2025, 12, 25, 10, 0)

        result = events_service.get_event_for_date(christmas)

        assert result is not None
        assert "Christmas" in result.get("name", "")
        assert result["is_special"] is True

    def test_manual_event_override(self, events_service, db_session, vendor_id):
        """Test that manual events override hardcoded dates."""
        from src.models.event_data import EventData

        # Override Christmas with custom event
        christmas = datetime(2025, 12, 25, 10, 0)
        custom_event = EventData(
            vendor_id=vendor_id,
            name="Custom Holiday Market",
            event_date=christmas,
            location="My Venue",
            expected_attendance=800,
            is_special=True,
            source="manual",
        )
        db_session.add(custom_event)
        db_session.commit()

        result = events_service.get_event_for_date(christmas)

        # Should return custom event, not hardcoded
        assert result["name"] == "Custom Holiday Market"
        assert result["expected_attendance"] == 800

    def test_no_event_returns_default(self, events_service):
        """Test that dates without events return default values."""
        # Random Tuesday in June
        random_date = datetime(2025, 6, 17, 10, 0)

        result = events_service.get_event_for_date(random_date)

        assert result is not None
        assert result["is_special"] is False
        assert result["expected_attendance"] <= 150  # Default attendance
