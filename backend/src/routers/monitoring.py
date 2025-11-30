"""
Monitoring Router

Exposes health check and metrics endpoints:
- GET /health - Basic health check (for load balancers)
- GET /health/live - Liveness probe (for Kubernetes)
- GET /health/ready - Readiness probe (for Kubernetes)
- GET /health/detailed - Detailed health checks for all services
- GET /metrics - Prometheus metrics endpoint
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from redis import Redis

from src.database import get_db
from src.cache import get_redis
from src.monitoring.health_checks import HealthChecker
from src.monitoring.metrics import metrics_response
from src.config import settings

router = APIRouter(tags=["monitoring"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Simple health check endpoint for load balancers. Returns 200 if service is running.",
    response_description="Service is healthy",
)
async def health_check():
    """
    Basic health check

    Returns a simple JSON response indicating the service is running.
    This endpoint is typically used by load balancers and should be
    lightweight and fast.

    **Response:**
    ```json
    {
        "status": "healthy",
        "version": "0.1.0",
        "environment": "production"
    }
    ```
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe. Returns 200 if the service is alive (not deadlocked).",
    response_description="Service is alive",
)
async def liveness_probe():
    """
    Liveness probe for Kubernetes

    This endpoint checks if the application is alive and not deadlocked.
    Kubernetes will restart the pod if this endpoint returns an error.

    This should only fail if the application is completely broken.
    It should NOT fail if external dependencies are unavailable.

    **Response:**
    ```json
    {
        "status": "alive",
        "version": "0.1.0"
    }
    ```
    """
    return {
        "status": "alive",
        "version": settings.app_version,
    }


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe. Returns 200 if the service is ready to accept traffic.",
    response_description="Service is ready",
)
async def readiness_probe(
    db: Session = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    """
    Readiness probe for Kubernetes

    This endpoint checks if the application is ready to accept traffic.
    It verifies that critical dependencies (database, Redis) are available.

    Kubernetes will remove the pod from the load balancer if this fails,
    but will NOT restart the pod.

    **Checks:**
    - Database connectivity
    - Redis connectivity (degraded if unavailable, not failed)

    **Response (Success):**
    ```json
    {
        "status": "ready",
        "version": "0.1.0",
        "database": "connected",
        "redis": "connected"
    }
    ```

    **Response (Not Ready):**
    ```json
    {
        "status": "not_ready",
        "version": "0.1.0",
        "database": "disconnected",
        "redis": "degraded"
    }
    ```
    """
    checker = HealthChecker(db_session=db, redis_client=redis)

    # Check critical services
    db_check = await checker.check_database()
    redis_check = await checker.check_redis()

    # Determine readiness
    # Database must be healthy
    # Redis can be degraded (we have fail-open)
    is_ready = db_check.status.value == "healthy"

    response = {
        "status": "ready" if is_ready else "not_ready",
        "version": settings.app_version,
        "database": db_check.status.value,
        "redis": redis_check.status.value,
    }

    if is_ready:
        return response
    else:
        # Return 503 Service Unavailable if not ready
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response,
        )


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed health checks",
    description="Comprehensive health checks for all services and dependencies.",
    response_description="Detailed health status",
)
async def detailed_health_check(
    db: Session = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    """
    Detailed health check

    Performs comprehensive health checks on all services:
    - Database (PostgreSQL)
    - Cache (Redis)
    - External APIs (Square, Weather, Events)
    - ML Model availability
    - System resources (disk, memory)

    **Response:**
    ```json
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "version": "0.1.0",
        "environment": "production",
        "checks": {
            "database": {
                "status": "healthy",
                "latency_ms": 5.23,
                "details": {...}
            },
            "redis": {...},
            "square": {...},
            "weather": {...},
            "events": {...},
            "ml_model": {...},
            "disk": {...},
            "memory": {...}
        },
        "total_latency_ms": 1250.42,
        "timestamp": "2025-01-30T12:00:00Z"
    }
    ```

    **Status Definitions:**
    - `healthy`: All systems operational
    - `degraded`: Some non-critical systems unavailable (using fallbacks)
    - `unhealthy`: Critical systems (database) unavailable
    """
    checker = HealthChecker(db_session=db, redis_client=redis)
    result = await checker.check_all()
    return result


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Prometheus-compatible metrics endpoint for monitoring and alerting.",
    response_description="Prometheus metrics in text format",
    include_in_schema=False,  # Don't include in OpenAPI docs (not JSON)
)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Exposes application metrics in Prometheus format for scraping.

    **Metrics Categories:**
    - HTTP request metrics (count, duration, in-progress, size)
    - Database query metrics (count, duration, errors)
    - External API metrics (Square, Weather, Events)
    - ML prediction metrics (count, duration, confidence)
    - Business metrics (recommendations, feedback, accuracy)
    - Cache metrics (hits, misses, errors)
    - System metrics (memory, CPU)

    **Example Prometheus configuration:**
    ```yaml
    scrape_configs:
      - job_name: 'marketprep'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/metrics'
        scrape_interval: 15s
    ```

    **Example metrics output:**
    ```
    # HELP marketprep_http_requests_total Total HTTP requests
    # TYPE marketprep_http_requests_total counter
    marketprep_http_requests_total{method="GET",endpoint="/api/v1/recommendations",status_code="200"} 1523.0

    # HELP marketprep_http_request_duration_seconds HTTP request duration in seconds
    # TYPE marketprep_http_request_duration_seconds histogram
    marketprep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/recommendations",le="0.1"} 1450.0
    marketprep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/recommendations",le="0.5"} 1520.0
    ```
    """
    return metrics_response()
