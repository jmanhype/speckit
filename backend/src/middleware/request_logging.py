"""Request logging middleware with correlation ID tracking.

Features:
- Correlation ID generation for request tracing
- Request/response logging
- Duration tracking
- Error tracking with detailed context
"""
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.logging_config import LogContext


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    def __init__(self, app: ASGIApp):
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Start timer
        start_time = time.time()

        # Log request
        with LogContext(
            correlation_id=correlation_id,
            request_method=request.method,
            request_path=request.url.path,
            request_ip=client_ip,
        ):
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    'event': 'request_started',
                    'query_params': dict(request.query_params),
                },
            )

            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log response
                logger.info(
                    f"Request completed: {request.method} {request.url.path} "
                    f"[{response.status_code}] in {duration_ms:.2f}ms",
                    extra={
                        'event': 'request_completed',
                        'status_code': response.status_code,
                        'duration_ms': round(duration_ms, 2),
                    },
                )

                # Add correlation ID to response headers
                response.headers['X-Correlation-ID'] = correlation_id

                return response

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log error
                logger.error(
                    f"Request failed: {request.method} {request.url.path} "
                    f"after {duration_ms:.2f}ms",
                    exc_info=True,
                    extra={
                        'event': 'request_failed',
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'duration_ms': round(duration_ms, 2),
                    },
                )

                # Re-raise exception
                raise

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
