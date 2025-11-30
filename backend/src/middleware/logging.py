"""Request logging middleware with correlation IDs.

Provides:
- Correlation ID generation and propagation
- Request/response logging
- Request timing
- Structured logging with context
"""
import logging
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses.

    Features:
    - Generates correlation ID for each request
    - Logs request method, path, and timing
    - Logs response status code and size
    - Adds correlation ID to response headers
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and log details.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with correlation ID header
        """
        # Generate correlation ID
        correlation_id = self._get_or_create_correlation_id(request)

        # Add to request state
        request.state.correlation_id = correlation_id

        # Log request
        start_time = time.time()

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error (will be caught by error handler)
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response

    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Get correlation ID from header or generate new one.

        Supports distributed tracing by accepting X-Correlation-ID header.

        Args:
            request: FastAPI request

        Returns:
            Correlation ID string
        """
        # Check if client provided correlation ID (for distributed tracing)
        correlation_id = request.headers.get("X-Correlation-ID")

        if correlation_id:
            logger.debug(
                f"Using client-provided correlation ID: {correlation_id}",
                extra={"correlation_id": correlation_id},
            )
            return correlation_id

        # Generate new correlation ID
        return str(uuid4())


class StructuredLogger:
    """Structured logger with correlation ID context.

    Usage:
        logger = StructuredLogger(request)
        logger.info("User authenticated", user_id=user_id)
    """

    def __init__(self, request: Request):
        """Initialize with request context.

        Args:
            request: FastAPI request with correlation_id in state
        """
        self.correlation_id = getattr(request.state, "correlation_id", None)
        self.logger = logging.getLogger(__name__)

    def _log(
        self,
        level: int,
        message: str,
        **kwargs,
    ) -> None:
        """Log message with correlation ID context.

        Args:
            level: Logging level
            message: Log message
            **kwargs: Additional context fields
        """
        extra = {"correlation_id": self.correlation_id, **kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)


def get_logger(request: Request) -> StructuredLogger:
    """FastAPI dependency to get structured logger.

    Usage:
        @router.get("/items")
        def list_items(logger: StructuredLogger = Depends(get_logger)):
            logger.info("Listing items", count=10)

    Args:
        request: FastAPI request (injected)

    Returns:
        StructuredLogger instance with correlation ID
    """
    return StructuredLogger(request)


def configure_logging() -> None:
    """Configure application logging.

    Sets up:
    - Log format with JSON structure
    - Log level from config
    - Console handler
    """
    from src.config import settings

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.log_level)

    # Create formatter (JSON format for production)
    if settings.environment == "production":
        # JSON formatter for structured logs
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                # Add extra fields
                if hasattr(record, "correlation_id"):
                    log_data["correlation_id"] = record.correlation_id

                if hasattr(record, "method"):
                    log_data["method"] = record.method

                if hasattr(record, "path"):
                    log_data["path"] = record.path

                if hasattr(record, "duration_ms"):
                    log_data["duration_ms"] = record.duration_ms

                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_data)

        formatter = JsonFormatter()
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
