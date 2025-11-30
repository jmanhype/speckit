"""Unit tests for weather service.

Tests weather API integration and caching behavior.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.weather import WeatherService


class TestWeatherService:
    """Test WeatherService functionality."""

    @pytest.fixture
    def weather_service(self):
        """Create weather service instance."""
        return WeatherService()

    @pytest.fixture
    def mock_weather_response(self):
        """Mock OpenWeather API response."""
        return {
            "list": [
                {
                    "main": {
                        "temp": 75.5,
                        "feels_like": 78.2,
                        "humidity": 65,
                    },
                    "weather": [
                        {
                            "main": "Rain",
                            "description": "light rain",
                        }
                    ],
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, weather_service, mock_weather_response):
        """Test successful weather forecast retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await weather_service.get_forecast(
                lat=37.7749,
                lon=-122.4194,
                target_date=datetime(2024, 12, 25),
            )

            assert result["temp_f"] == 75.5
            assert result["feels_like_f"] == 78.2
            assert result["humidity"] == 65
            assert result["condition"] == "rain"
            assert result["description"] == "light rain"

    @pytest.mark.asyncio
    async def test_get_forecast_api_error(self, weather_service):
        """Test weather forecast with API error falls back to defaults."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await weather_service.get_forecast(
                lat=37.7749,
                lon=-122.4194,
            )

            # Should return default weather
            assert result["temp_f"] == 70.0
            assert result["feels_like_f"] == 70.0
            assert result["humidity"] == 50.0
            assert result["condition"] == "clear"

    @pytest.mark.asyncio
    async def test_get_forecast_no_api_key(self):
        """Test weather forecast without API key uses defaults."""
        with patch("src.services.weather.settings") as mock_settings:
            mock_settings.openweather_api_key = None

            service = WeatherService()
            result = await service.get_forecast(lat=37.7749, lon=-122.4194)

            assert result["temp_f"] == 70.0
            assert result["condition"] == "clear"
            assert "unavailable" in result["description"].lower()

    @pytest.mark.asyncio
    async def test_get_forecast_network_error(self, weather_service):
        """Test weather forecast with network error falls back to defaults."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            result = await weather_service.get_forecast(
                lat=37.7749,
                lon=-122.4194,
            )

            # Should return default weather
            assert result["temp_f"] == 70.0
            assert result["condition"] == "clear"

    @pytest.mark.asyncio
    async def test_get_forecast_malformed_response(self, weather_service):
        """Test weather forecast with malformed API response."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"error": "invalid"}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await weather_service.get_forecast(
                lat=37.7749,
                lon=-122.4194,
            )

            # Should return default weather when response is malformed
            assert result["temp_f"] == 70.0
            assert result["condition"] == "clear"

    def test_default_weather(self, weather_service):
        """Test default weather data structure."""
        result = weather_service._get_default_weather()

        assert "temp_f" in result
        assert "feels_like_f" in result
        assert "humidity" in result
        assert "condition" in result
        assert "description" in result
        assert result["temp_f"] == 70.0
        assert result["condition"] == "clear"

    @pytest.mark.asyncio
    async def test_weather_conditions_mapping(self, weather_service):
        """Test various weather conditions are mapped correctly."""
        test_cases = [
            ("Clear", "clear"),
            ("Clouds", "clouds"),
            ("Rain", "rain"),
            ("Snow", "snow"),
            ("Thunderstorm", "thunderstorm"),
        ]

        for api_condition, expected_condition in test_cases:
            mock_response = {
                "list": [
                    {
                        "main": {"temp": 70, "feels_like": 70, "humidity": 50},
                        "weather": [{"main": api_condition, "description": "test"}],
                    }
                ]
            }

            with patch("httpx.AsyncClient") as mock_client:
                mock_resp = AsyncMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = mock_response

                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_resp
                )

                result = await weather_service.get_forecast(lat=37.7749, lon=-122.4194)
                assert result["condition"] == expected_condition.lower()
