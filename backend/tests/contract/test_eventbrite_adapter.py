"""Contract tests for Eventbrite API adapter.

Tests that we correctly interact with the Eventbrite API.
Uses mocked responses to test contract compliance.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from src.adapters.eventbrite_adapter import EventbriteAdapter


class TestEventbriteAdapter:
    """Contract tests for Eventbrite API integration."""

    @pytest.fixture
    def adapter(self):
        """Create Eventbrite adapter with test API key."""
        return EventbriteAdapter(api_key="test_api_key_12345")

    @pytest.fixture
    def mock_eventbrite_response(self):
        """Mock Eventbrite API response."""
        return {
            "events": [
                {
                    "id": "123456789",
                    "name": {"text": "Summer Food Festival"},
                    "description": {"text": "Annual food festival in downtown"},
                    "start": {
                        "local": "2025-06-15T10:00:00",
                        "timezone": "America/Los_Angeles",
                    },
                    "end": {
                        "local": "2025-06-15T18:00:00",
                        "timezone": "America/Los_Angeles",
                    },
                    "venue": {
                        "name": "Downtown Plaza",
                        "address": {
                            "address_1": "123 Main St",
                            "city": "San Francisco",
                            "region": "CA",
                            "postal_code": "94102",
                            "latitude": "37.7749",
                            "longitude": "-122.4194",
                        },
                    },
                    "capacity": 5000,
                    "is_free": False,
                },
                {
                    "id": "987654321",
                    "name": {"text": "Music in the Park"},
                    "description": {"text": "Free outdoor concert"},
                    "start": {
                        "local": "2025-06-15T14:00:00",
                        "timezone": "America/Los_Angeles",
                    },
                    "end": {
                        "local": "2025-06-15T17:00:00",
                        "timezone": "America/Los_Angeles",
                    },
                    "venue": {
                        "name": "City Park",
                        "address": {
                            "address_1": "456 Park Ave",
                            "city": "San Francisco",
                            "region": "CA",
                            "postal_code": "94103",
                            "latitude": "37.7849",
                            "longitude": "-122.4294",
                        },
                    },
                    "capacity": 2000,
                    "is_free": True,
                },
            ],
            "pagination": {
                "object_count": 2,
                "page_number": 1,
                "page_size": 50,
                "page_count": 1,
            },
        }

    @pytest.mark.asyncio
    async def test_search_events_by_location(self, adapter, mock_eventbrite_response):
        """Test searching for events by location and date."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_eventbrite_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Search for events
            target_date = datetime(2025, 6, 15)
            events = await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            # Verify results
            assert len(events) == 2
            assert events[0]["name"] == "Summer Food Festival"
            assert events[0]["expected_attendance"] == 5000
            assert events[1]["name"] == "Music in the Park"
            assert events[1]["expected_attendance"] == 2000

    @pytest.mark.asyncio
    async def test_parse_event_data_correctly(self, adapter, mock_eventbrite_response):
        """Test that Eventbrite event data is parsed correctly."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_eventbrite_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            target_date = datetime(2025, 6, 15)
            events = await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            first_event = events[0]

            # Verify all required fields are present
            assert "name" in first_event
            assert "event_date" in first_event
            assert "location" in first_event
            assert "latitude" in first_event
            assert "longitude" in first_event
            assert "expected_attendance" in first_event
            assert "is_special" in first_event
            assert "source" in first_event

            # Verify correct parsing
            assert first_event["location"] == "Downtown Plaza"
            assert first_event["latitude"] == Decimal("37.7749")
            assert first_event["longitude"] == Decimal("-122.4194")
            assert first_event["source"] == "eventbrite"

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, adapter):
        """Test graceful handling of API errors."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            target_date = datetime(2025, 6, 15)
            events = await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            # Should return empty list on error
            assert events == []

    @pytest.mark.asyncio
    async def test_handles_missing_api_key(self):
        """Test that missing API key is handled."""
        adapter = EventbriteAdapter(api_key=None)

        target_date = datetime(2025, 6, 15)
        events = await adapter.search_events(
            latitude=37.7749,
            longitude=-122.4194,
            radius_miles=10,
            start_date=target_date,
            end_date=target_date + timedelta(days=1),
        )

        # Should return empty list when no API key
        assert events == []

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self, adapter, mock_eventbrite_response):
        """Test that date range filtering is applied correctly."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_eventbrite_response

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            target_date = datetime(2025, 6, 15)
            await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            # Verify API was called with correct date parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]

            assert "start_date.range_start" in params
            assert "start_date.range_end" in params

    @pytest.mark.asyncio
    async def test_converts_capacity_to_attendance(self, adapter, mock_eventbrite_response):
        """Test that event capacity is converted to expected attendance."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_eventbrite_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            target_date = datetime(2025, 6, 15)
            events = await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            # Capacity should be used as expected_attendance
            assert events[0]["expected_attendance"] == 5000
            assert events[1]["expected_attendance"] == 2000

    @pytest.mark.asyncio
    async def test_marks_large_events_as_special(self, adapter, mock_eventbrite_response):
        """Test that large events are marked as special."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_eventbrite_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            target_date = datetime(2025, 6, 15)
            events = await adapter.search_events(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=10,
                start_date=target_date,
                end_date=target_date + timedelta(days=1),
            )

            # Events with >1000 capacity should be marked special
            assert events[0]["is_special"] is True  # 5000 capacity
            assert events[1]["is_special"] is True  # 2000 capacity
