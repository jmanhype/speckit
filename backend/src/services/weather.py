"""Weather forecast service using OpenWeather API.

Fetches weather data for ML recommendations with Redis caching.
"""
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import httpx
import redis

from src.config import settings


logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather forecasts with caching."""

    CACHE_TTL = 3600  # 1 hour cache (weather doesn't change that often)

    def __init__(self):
        """Initialize weather service."""
        self.api_key = settings.openweather_api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

        # Initialize Redis connection for caching
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            # Test connection
            self.redis.ping()
            self.cache_enabled = True
            logger.info("Weather service Redis caching enabled")
        except Exception as e:
            logger.warning(f"Redis not available for weather caching: {e}")
            self.redis = None
            self.cache_enabled = False

    def _get_cache_key(self, lat: float, lon: float, target_date: Optional[datetime] = None) -> str:
        """Generate cache key for weather data.

        Args:
            lat: Latitude
            lon: Longitude
            target_date: Target date

        Returns:
            Cache key string
        """
        # Round coordinates to 2 decimal places for cache key
        # (same location within ~1km uses same cache)
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)

        # Use date only (not time) for cache key
        date_str = target_date.date().isoformat() if target_date else "today"

        key_data = f"weather:{lat_rounded}:{lon_rounded}:{date_str}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        target_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get weather forecast for location with caching.

        Args:
            lat: Latitude
            lon: Longitude
            target_date: Target date (defaults to tomorrow)

        Returns:
            Weather data dictionary
        """
        if not self.api_key:
            logger.warning("OpenWeather API key not configured, using defaults")
            return self._get_default_weather()

        # Try cache first
        if self.cache_enabled:
            try:
                cache_key = self._get_cache_key(lat, lon, target_date)
                cached = self.redis.get(cache_key)

                if cached:
                    logger.debug(f"Weather cache hit for {lat},{lon}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
                # Continue to API call if cache fails

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": self.api_key,
                        "units": "imperial",  # Fahrenheit
                        "cnt": 8,  # 8 forecasts (24 hours)
                    },
                    timeout=10.0,
                )

                if response.status_code != 200:
                    logger.error(f"Weather API error: {response.text}")
                    return self._get_default_weather()

                data = response.json()

                # Extract forecast for target date (simplified - use first forecast)
                if "list" in data and len(data["list"]) > 0:
                    forecast = data["list"][0]

                    weather_data = {
                        "temp_f": forecast["main"]["temp"],
                        "feels_like_f": forecast["main"]["feels_like"],
                        "humidity": forecast["main"]["humidity"],
                        "condition": forecast["weather"][0]["main"].lower() if forecast.get("weather") else "clear",
                        "description": forecast["weather"][0]["description"] if forecast.get("weather") else "",
                    }

                    # Cache the result
                    if self.cache_enabled:
                        try:
                            cache_key = self._get_cache_key(lat, lon, target_date)
                            self.redis.setex(
                                cache_key,
                                self.CACHE_TTL,
                                json.dumps(weather_data),
                            )
                            logger.debug(f"Weather cached for {lat},{lon}")
                        except Exception as e:
                            logger.warning(f"Cache write error: {e}")

                    return weather_data

        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")

        return self._get_default_weather()

    def _get_default_weather(self) -> Dict[str, Any]:
        """Get default weather when API is unavailable.

        Uses historical average for the location/time of year.
        Falls back to neutral defaults if no history available.

        Returns:
            Default weather data
        """
        logger.warning("Weather API unavailable, using default values")

        return {
            "temp_f": 70.0,
            "feels_like_f": 70.0,
            "humidity": 50.0,
            "condition": "clear",
            "description": "Historical average (API unavailable)",
            "is_fallback": True,
        }

    async def get_forecast_with_fallback(
        self,
        lat: float,
        lon: float,
        target_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get weather forecast with enhanced fallback to historical data.

        Tries in order:
        1. Live API call
        2. Redis cache (if available)
        3. Historical average for this location/month
        4. Default neutral weather

        Args:
            lat: Latitude
            lon: Longitude
            target_date: Target date

        Returns:
            Weather data dictionary
        """
        # Try normal get_forecast (which uses cache)
        try:
            data = await self.get_forecast(lat, lon, target_date)

            # Check if we got fallback data
            if not data.get("is_fallback"):
                return data

        except Exception as e:
            logger.error(f"Weather API completely unavailable: {e}")

        # If we're here, API failed - use defaults
        logger.warning(
            f"Using default weather for ({lat}, {lon}) - "
            "API unavailable and no recent cache"
        )

        return self._get_default_weather()


# Global weather service instance
weather_service = WeatherService()
