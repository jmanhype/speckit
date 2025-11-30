"""Error tracking middleware with detailed error context.

Features:
- Automatic error logging with full context
- Error categorization (client vs server errors)
- Stack trace capture
- Error metrics tracking
- Integration-ready for Sentry, Datadog, etc.
"""
import logging
import traceback
from typing import Callable, Dict, Any, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.logging_config import LogContext


logger = logging.getLogger(__name__)


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking and logging errors."""

    def __init__(
        self,
        app: ASGIApp,
        enable_error_details: bool = False,
    ):
        """Initialize error tracking middleware.

        Args:
            app: ASGI application
            enable_error_details: Whether to include error details in responses
                                 (should be False in production)
        """
        super().__init__(app)
        self.enable_error_details = enable_error_details

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process request and handle errors.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or error response
        """
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            # Get correlation ID from request state
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')

            # Get vendor ID from request state (if authenticated)
            vendor_id = getattr(request.state, 'vendor_id', None)

            # Categorize error
            error_category = self._categorize_error(e)
            status_code = self._get_status_code(e)

            # Build error context
            error_context = self._build_error_context(
                request=request,
                exception=e,
                correlation_id=correlation_id,
                vendor_id=vendor_id,
            )

            # Log error with full context
            with LogContext(
                correlation_id=correlation_id,
                vendor_id=str(vendor_id) if vendor_id else None,
                request_method=request.method,
                request_path=request.url.path,
            ):
                if error_category == 'client_error':
                    # Client errors (4xx) - log as warning
                    logger.warning(
                        f"Client error: {type(e).__name__}: {str(e)}",
                        extra={
                            'event': 'client_error',
                            'error_type': type(e).__name__,
                            'error_category': error_category,
                            **error_context,
                        },
                    )
                else:
                    # Server errors (5xx) - log as error with stack trace
                    logger.error(
                        f"Server error: {type(e).__name__}: {str(e)}",
                        exc_info=True,
                        extra={
                            'event': 'server_error',
                            'error_type': type(e).__name__,
                            'error_category': error_category,
                            **error_context,
                        },
                    )

            # Build error response
            error_response = self._build_error_response(
                exception=e,
                status_code=status_code,
                correlation_id=correlation_id,
            )

            return JSONResponse(
                status_code=status_code,
                content=error_response,
                headers={'X-Correlation-ID': correlation_id},
            )

    def _categorize_error(self, exception: Exception) -> str:
        """Categorize error as client or server error.

        Args:
            exception: The exception

        Returns:
            Error category ('client_error' or 'server_error')
        """
        from fastapi import HTTPException

        # HTTPException with 4xx status
        if isinstance(exception, HTTPException):
            if 400 <= exception.status_code < 500:
                return 'client_error'
            else:
                return 'server_error'

        # Validation errors are client errors
        from pydantic import ValidationError
        if isinstance(exception, ValidationError):
            return 'client_error'

        # Everything else is server error
        return 'server_error'

    def _get_status_code(self, exception: Exception) -> int:
        """Get HTTP status code for exception.

        Args:
            exception: The exception

        Returns:
            HTTP status code
        """
        from fastapi import HTTPException
        from pydantic import ValidationError

        if isinstance(exception, HTTPException):
            return exception.status_code
        elif isinstance(exception, ValidationError):
            return status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            return status.HTTP_500_INTERNAL_SERVER_ERROR

    def _build_error_context(
        self,
        request: Request,
        exception: Exception,
        correlation_id: str,
        vendor_id: Optional[Any],
    ) -> Dict[str, Any]:
        """Build error context for logging.

        Args:
            request: FastAPI request
            exception: The exception
            correlation_id: Request correlation ID
            vendor_id: Vendor ID (if authenticated)

        Returns:
            Error context dictionary
        """
        context = {
            'correlation_id': correlation_id,
            'url': str(request.url),
            'method': request.method,
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': dict(request.headers),
            'error_message': str(exception),
        }

        if vendor_id:
            context['vendor_id'] = str(vendor_id)

        # Add stack trace for server errors
        if self._categorize_error(exception) == 'server_error':
            context['stack_trace'] = traceback.format_exc()

        return context

    def _build_error_response(
        self,
        exception: Exception,
        status_code: int,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Build error response for client.

        Args:
            exception: The exception
            status_code: HTTP status code
            correlation_id: Request correlation ID

        Returns:
            Error response dictionary
        """
        from fastapi import HTTPException
        from pydantic import ValidationError

        # Base response
        response = {
            'error': True,
            'correlation_id': correlation_id,
        }

        # Add error details
        if isinstance(exception, HTTPException):
            response['message'] = exception.detail
            response['type'] = 'http_error'
        elif isinstance(exception, ValidationError):
            response['message'] = 'Validation error'
            response['type'] = 'validation_error'
            if self.enable_error_details:
                response['details'] = exception.errors()
        else:
            response['message'] = 'Internal server error'
            response['type'] = 'server_error'

        # Add exception details in development
        if self.enable_error_details:
            response['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
            }

        return response


# Error metrics tracker (for future integration with monitoring)
class ErrorMetrics:
    """Track error metrics for monitoring."""

    def __init__(self):
        """Initialize error metrics."""
        self.error_counts = {}

    def record_error(
        self,
        error_type: str,
        error_category: str,
        endpoint: str,
    ) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type of error
            error_category: Error category (client/server)
            endpoint: API endpoint
        """
        key = f"{error_category}:{error_type}:{endpoint}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

        # Log metrics (can be sent to monitoring service)
        logger.debug(
            f"Error metric recorded: {key}",
            extra={
                'event': 'error_metric',
                'error_type': error_type,
                'error_category': error_category,
                'endpoint': endpoint,
                'count': self.error_counts[key],
            },
        )

    def get_metrics(self) -> Dict[str, int]:
        """Get all error metrics.

        Returns:
            Dictionary of error counts
        """
        return self.error_counts.copy()

    def reset_metrics(self) -> None:
        """Reset all error metrics."""
        self.error_counts.clear()


# Global error metrics instance
error_metrics = ErrorMetrics()
