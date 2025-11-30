"""
Health Check System for MarketPrep

Provides detailed health checks for all service dependencies:
- Database (PostgreSQL)
- Cache (Redis)
- External APIs (Square, Weather, Events)
- ML Model availability
- Disk space
- Memory usage

Each check returns:
- status: "healthy" | "degraded" | "unhealthy"
- latency_ms: Response time
- details: Additional info
- timestamp: ISO 8601 UTC
"""

import asyncio
import psutil
import shutil
import time
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session
from redis import Redis

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResult:
    """Result of a health check"""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        latency_ms: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.status = status
        self.latency_ms = latency_ms
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details,
            "timestamp": self.timestamp,
        }


class HealthChecker:
    """Orchestrates all health checks"""

    def __init__(
        self,
        db_session: Optional[Session] = None,
        redis_client: Optional[Redis] = None,
    ):
        self.db_session = db_session
        self.redis_client = redis_client

    async def check_all(self) -> Dict[str, Any]:
        """
        Run all health checks in parallel

        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "version": "0.1.0",
                "environment": "production",
                "checks": {
                    "database": {...},
                    "redis": {...},
                    "square": {...},
                    "weather": {...},
                    "events": {...},
                    "ml_model": {...},
                    "disk": {...},
                    "memory": {...}
                },
                "timestamp": "2025-01-30T12:00:00Z"
            }
        """
        start_time = time.time()

        # Run all checks in parallel (mix of sync and async)
        results = await asyncio.gather(
            asyncio.to_thread(self.check_database),
            asyncio.to_thread(self.check_redis),
            self.check_square_api(),
            self.check_weather_api(),
            self.check_events_api(),
            asyncio.to_thread(self.check_ml_model),
            asyncio.to_thread(self.check_disk_space),
            asyncio.to_thread(self.check_memory_usage),
            return_exceptions=True,
        )

        # Process results
        checks = {}
        check_names = [
            "database",
            "redis",
            "square",
            "weather",
            "events",
            "ml_model",
            "disk",
            "memory",
        ]

        for name, result in zip(check_names, results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {name}: {result}")
                checks[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    details={"error": str(result)},
                ).to_dict()
            else:
                checks[name] = result.to_dict()

        # Determine overall status
        overall_status = self._calculate_overall_status(checks)

        total_latency_ms = (time.time() - start_time) * 1000

        return {
            "status": overall_status.value,
            "version": settings.version,
            "environment": settings.environment,
            "checks": checks,
            "total_latency_ms": round(total_latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _calculate_overall_status(self, checks: Dict[str, Dict]) -> HealthStatus:
        """
        Calculate overall health status from individual checks

        Logic:
        - If any critical service (database, redis) is unhealthy -> UNHEALTHY
        - If any critical service is degraded -> DEGRADED
        - If any non-critical service is unhealthy -> DEGRADED
        - Otherwise -> HEALTHY
        """
        critical_services = ["database", "redis"]

        for service in critical_services:
            if checks[service]["status"] == HealthStatus.UNHEALTHY.value:
                return HealthStatus.UNHEALTHY

        for service in critical_services:
            if checks[service]["status"] == HealthStatus.DEGRADED.value:
                return HealthStatus.DEGRADED

        for check in checks.values():
            if check["status"] == HealthStatus.UNHEALTHY.value:
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def check_database(self) -> HealthCheckResult:
        """Check PostgreSQL database connectivity and query performance"""
        start_time = time.time()

        try:
            if not self.db_session:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    details={"error": "No database session provided"},
                )

            # Execute simple query
            result = self.db_session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()

            latency_ms = (time.time() - start_time) * 1000

            if row and row[0] == 1:
                status = HealthStatus.HEALTHY
                if latency_ms > 100:  # Slow query threshold
                    status = HealthStatus.DEGRADED

                return HealthCheckResult(
                    name="database",
                    status=status,
                    latency_ms=latency_ms,
                    details={
                        "connection": "active",
                        "query_latency_ms": round(latency_ms, 2),
                    },
                )
            else:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency_ms,
                    details={"error": "Query returned unexpected result"},
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity and latency"""
        start_time = time.time()

        try:
            if not self.redis_client:
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.DEGRADED,  # Degraded not unhealthy (fail-open)
                    latency_ms=0,
                    details={"error": "No Redis client provided", "impact": "Rate limiting disabled"},
                )

            # Execute PING command
            pong = self.redis_client.ping()
            latency_ms = (time.time() - start_time) * 1000

            if pong:
                status = HealthStatus.HEALTHY
                if latency_ms > 50:  # Redis should be very fast
                    status = HealthStatus.DEGRADED

                return HealthCheckResult(
                    name="redis",
                    status=status,
                    latency_ms=latency_ms,
                    details={
                        "connection": "active",
                        "ping_latency_ms": round(latency_ms, 2),
                    },
                )
            else:
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency_ms,
                    details={"error": "PING failed", "impact": "Rate limiting disabled"},
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Redis health check failed (fail-open): {e}")
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                details={"error": str(e), "impact": "Rate limiting disabled"},
            )

    async def check_square_api(self) -> HealthCheckResult:
        """Check Square API availability"""
        start_time = time.time()

        try:
            if not settings.square_application_id:
                return HealthCheckResult(
                    name="square",
                    status=HealthStatus.DEGRADED,
                    latency_ms=0,
                    details={"configured": False, "impact": "Using cached data"},
                )

            # Simple health check - try to list locations (lightweight)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.square_base_url}/v2/locations",
                    headers={
                        "Square-Version": "2023-12-13",
                        "Authorization": f"Bearer {settings.square_application_secret}",
                    },
                )

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    if latency_ms > 2000:  # 2 second threshold
                        status = HealthStatus.DEGRADED

                    return HealthCheckResult(
                        name="square",
                        status=status,
                        latency_ms=latency_ms,
                        details={
                            "api_version": "2023-12-13",
                            "response_status": 200,
                        },
                    )
                else:
                    return HealthCheckResult(
                        name="square",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency_ms,
                        details={
                            "error": f"HTTP {response.status_code}",
                            "impact": "Using cached data",
                        },
                    )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Square API health check failed: {e}")
            return HealthCheckResult(
                name="square",
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                details={"error": str(e), "impact": "Using cached data"},
            )

    async def check_weather_api(self) -> HealthCheckResult:
        """Check OpenWeather API availability"""
        start_time = time.time()

        try:
            if not settings.openweather_api_key:
                return HealthCheckResult(
                    name="weather",
                    status=HealthStatus.DEGRADED,
                    latency_ms=0,
                    details={"configured": False, "impact": "Using default weather"},
                )

            # Simple API check - get weather for a known location
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": 37.7749,  # San Francisco
                        "lon": -122.4194,
                        "appid": settings.openweather_api_key,
                    },
                )

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    if latency_ms > 3000:  # 3 second threshold
                        status = HealthStatus.DEGRADED

                    return HealthCheckResult(
                        name="weather",
                        status=status,
                        latency_ms=latency_ms,
                        details={"response_status": 200},
                    )
                else:
                    return HealthCheckResult(
                        name="weather",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency_ms,
                        details={
                            "error": f"HTTP {response.status_code}",
                            "impact": "Using fallback weather data",
                        },
                    )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Weather API health check failed: {e}")
            return HealthCheckResult(
                name="weather",
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                details={"error": str(e), "impact": "Using fallback weather data"},
            )

    async def check_events_api(self) -> HealthCheckResult:
        """Check Eventbrite API availability"""
        start_time = time.time()

        try:
            if not settings.eventbrite_api_key:
                return HealthCheckResult(
                    name="events",
                    status=HealthStatus.DEGRADED,
                    latency_ms=0,
                    details={"configured": False, "impact": "Using database events only"},
                )

            # Simple API check
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://www.eventbriteapi.com/v3/users/me/",
                    headers={"Authorization": f"Bearer {settings.eventbrite_api_key}"},
                )

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    if latency_ms > 3000:  # 3 second threshold
                        status = HealthStatus.DEGRADED

                    return HealthCheckResult(
                        name="events",
                        status=status,
                        latency_ms=latency_ms,
                        details={"response_status": 200},
                    )
                else:
                    return HealthCheckResult(
                        name="events",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency_ms,
                        details={
                            "error": f"HTTP {response.status_code}",
                            "impact": "Using database events only",
                        },
                    )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Events API health check failed: {e}")
            return HealthCheckResult(
                name="events",
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                details={"error": str(e), "impact": "Using database events only"},
            )

    def check_ml_model(self) -> HealthCheckResult:
        """Check ML model availability"""
        start_time = time.time()

        try:
            # Check if model files exist
            import os

            # Base directory is the backend directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "ml_models", "recommendation_model.pkl")
            scaler_path = os.path.join(base_dir, "ml_models", "scaler.pkl")

            model_exists = os.path.exists(model_path)
            scaler_exists = os.path.exists(scaler_path)

            latency_ms = (time.time() - start_time) * 1000

            if model_exists and scaler_exists:
                return HealthCheckResult(
                    name="ml_model",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                    details={
                        "model_loaded": True,
                        "scaler_loaded": True,
                    },
                )
            else:
                return HealthCheckResult(
                    name="ml_model",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency_ms,
                    details={
                        "model_loaded": model_exists,
                        "scaler_loaded": scaler_exists,
                        "impact": "Using fallback heuristics",
                    },
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"ML model health check failed: {e}")
            return HealthCheckResult(
                name="ml_model",
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                details={"error": str(e), "impact": "Using fallback heuristics"},
            )

    def check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        start_time = time.time()

        try:
            disk_usage = shutil.disk_usage("/")
            total_gb = disk_usage.total / (1024 ** 3)
            used_gb = disk_usage.used / (1024 ** 3)
            free_gb = disk_usage.free / (1024 ** 3)
            percent_used = (disk_usage.used / disk_usage.total) * 100

            latency_ms = (time.time() - start_time) * 1000

            # Determine status based on free space
            if percent_used < 80:
                status = HealthStatus.HEALTHY
            elif percent_used < 90:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                name="disk",
                status=status,
                latency_ms=latency_ms,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_used": round(percent_used, 2),
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Disk space health check failed: {e}")
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage"""
        start_time = time.time()

        try:
            memory = psutil.virtual_memory()

            latency_ms = (time.time() - start_time) * 1000

            # Determine status based on memory usage
            if memory.percent < 80:
                status = HealthStatus.HEALTHY
            elif memory.percent < 90:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                name="memory",
                status=status,
                latency_ms=latency_ms,
                details={
                    "total_gb": round(memory.total / (1024 ** 3), 2),
                    "available_gb": round(memory.available / (1024 ** 3), 2),
                    "percent_used": round(memory.percent, 2),
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Memory usage health check failed: {e}")
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                details={"error": str(e)},
            )
