"""Global error handling middleware.

Provides centralized exception handling with:
- Standardized error response format
- Error logging with correlation IDs
- HTTP status code mapping
- Production-safe error messages
"""
import logging
import traceback
from typing import Callable, Any, Dict
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings


logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response format."""

    def __init__(
        self,
        error_id: str,
        message: str,
        details: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        """Initialize error response.

        Args:
            error_id: Unique error identifier for correlation
            message: User-friendly error message
            details: Technical error details (only in debug mode)
            status_code: HTTP status code
        """
        self.error_id = error_id
        self.message = message
        self.details = details if settings.debug else None
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        response: Dict[str, Any] = {
            "error_id": self.error_id,
            "message": self.message,
        }

        if self.details is not None:
            response["details"] = self.details

        return response


class GlobalErrorHandler(BaseHTTPMiddleware):
    """Middleware for global exception handling.

    Catches all unhandled exceptions and returns standardized error responses.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> JSONResponse:
        """Process request and handle any exceptions.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or error response
        """
        error_id = str(uuid4())

        # Add error_id to request state for logging
        request.state.error_id = error_id

        try:
            response = await call_next(request)
            return response

        except SQLAlchemyError as e:
            return self._handle_database_error(e, error_id, request)

        except ValueError as e:
            return self._handle_validation_error(e, error_id, request)

        except Exception as e:
            return self._handle_generic_error(e, error_id, request)

    def _handle_database_error(
        self,
        error: SQLAlchemyError,
        error_id: str,
        request: Request,
    ) -> JSONResponse:
        """Handle database-related errors.

        Args:
            error: SQLAlchemy exception
            error_id: Error correlation ID
            request: FastAPI request

        Returns:
            Error response
        """
        logger.error(
            f"Database error [{error_id}]: {str(error)}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )

        error_response = ErrorResponse(
            error_id=error_id,
            message="Database error occurred",
            details=str(error) if settings.debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
        )

    def _handle_validation_error(
        self,
        error: ValueError,
        error_id: str,
        request: Request,
    ) -> JSONResponse:
        """Handle validation errors.

        Args:
            error: ValueError exception
            error_id: Error correlation ID
            request: FastAPI request

        Returns:
            Error response
        """
        logger.warning(
            f"Validation error [{error_id}]: {str(error)}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
            },
        )

        error_response = ErrorResponse(
            error_id=error_id,
            message="Validation error",
            details=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
        )

    def _handle_generic_error(
        self,
        error: Exception,
        error_id: str,
        request: Request,
    ) -> JSONResponse:
        """Handle generic unhandled exceptions.

        Args:
            error: Exception
            error_id: Error correlation ID
            request: FastAPI request

        Returns:
            Error response
        """
        logger.error(
            f"Unhandled exception [{error_id}]: {str(error)}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
            exc_info=True,
        )

        error_response = ErrorResponse(
            error_id=error_id,
            message="Internal server error",
            details=f"{type(error).__name__}: {str(error)}" if settings.debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
        )


def setup_exception_handlers(app) -> None:
    """Setup custom exception handlers for FastAPI.

    Args:
        app: FastAPI application instance
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import IntegrityError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTPException."""
        error_id = getattr(request.state, "error_id", str(uuid4()))

        logger.warning(
            f"HTTP exception [{error_id}]: {exc.status_code} - {exc.detail}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_id": error_id,
                "message": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        """Handle Pydantic validation errors."""
        error_id = getattr(request.state, "error_id", str(uuid4()))

        logger.warning(
            f"Request validation error [{error_id}]: {exc.errors()}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_id": error_id,
                "message": "Validation error",
                "details": exc.errors() if settings.debug else "Invalid request data",
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """Handle database integrity constraint violations."""
        error_id = getattr(request.state, "error_id", str(uuid4()))

        logger.error(
            f"Database integrity error [{error_id}]: {str(exc)}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )

        # Check for common constraint violations
        error_msg = "Database constraint violation"
        if "unique" in str(exc).lower():
            error_msg = "Resource already exists"
        elif "foreign key" in str(exc).lower():
            error_msg = "Referenced resource does not exist"

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error_id": error_id,
                "message": error_msg,
                "details": str(exc) if settings.debug else None,
            },
        )
