"""
Metrics Middleware for HTTP Request Tracking

Automatically collects Prometheus metrics for all HTTP requests:
- Request count by method/endpoint/status
- Request duration
- Requests in progress
- Response size

Integrates with src/monitoring/metrics.py
"""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.monitoring.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_response_size_bytes,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics for Prometheus

    Tracks:
    - Total requests (by method, endpoint, status code)
    - Request duration (by method, endpoint)
    - Concurrent requests (by method, endpoint)
    - Response size (by method, endpoint)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract endpoint path (normalize to avoid high cardinality)
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method

        # Track requests in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Start timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            status_code = response.status_code

            # Increment request counter
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            # Record duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            # Record response size if available
            if hasattr(response, "body") and response.body:
                response_size = len(response.body)
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(response_size)

            return response

        except Exception as e:
            # Record error
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            logger.error(f"Request failed: {method} {endpoint} - {e}")
            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path to avoid high cardinality in metrics

        Examples:
            /api/v1/recommendations/123e4567-e89b-12d3-a456-426614174000
            -> /api/v1/recommendations/{id}

            /api/v1/products/abc-def-ghi/inventory
            -> /api/v1/products/{id}/inventory

        This prevents creating a separate metric for each UUID/ID,
        which would cause memory issues in Prometheus.
        """
        # Skip metrics endpoint itself
        if path == "/metrics":
            return "/metrics"

        # Skip health endpoints
        if path in ["/health", "/health/live", "/health/ready"]:
            return path

        # Split path into segments
        segments = path.split("/")
        normalized_segments = []

        for segment in segments:
            if not segment:  # Empty segment (e.g., leading slash)
                continue

            # Check if segment looks like a UUID
            if self._is_uuid(segment):
                normalized_segments.append("{id}")
            # Check if segment is numeric
            elif segment.isdigit():
                normalized_segments.append("{id}")
            # Check if segment looks like a date (YYYY-MM-DD)
            elif self._is_date(segment):
                normalized_segments.append("{date}")
            else:
                normalized_segments.append(segment)

        return "/" + "/".join(normalized_segments)

    @staticmethod
    def _is_uuid(value: str) -> bool:
        """Check if string looks like a UUID"""
        if len(value) == 36 and value.count("-") == 4:
            # Simple heuristic: 36 chars with 4 dashes
            return True
        # Hex format without dashes (32 chars)
        if len(value) == 32 and all(c in "0123456789abcdefABCDEF" for c in value):
            return True
        return False

    @staticmethod
    def _is_date(value: str) -> bool:
        """Check if string looks like a date (YYYY-MM-DD)"""
        if len(value) == 10 and value.count("-") == 2:
            parts = value.split("-")
            if len(parts) == 3:
                try:
                    year, month, day = parts
                    if (
                        year.isdigit() and len(year) == 4 and
                        month.isdigit() and 1 <= int(month) <= 12 and
                        day.isdigit() and 1 <= int(day) <= 31
                    ):
                        return True
                except ValueError:
                    pass
        return False
