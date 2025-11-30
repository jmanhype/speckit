"""Authentication middleware for JWT token validation and RLS context.

Provides:
- JWT token extraction from Authorization header
- Token validation using AuthService
- Vendor context injection into request.state
- PostgreSQL Row-Level Security (RLS) session variable setting
- FastAPI dependency for getting current authenticated vendor
"""
from typing import Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.services.auth_service import (
    AuthService,
    TokenType,
    TokenExpiredError,
    InvalidTokenError,
    InvalidTokenTypeError,
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and RLS context setting.

    Extracts JWT token from Authorization header, validates it,
    and sets vendor_id in request.state and PostgreSQL session.
    """

    def __init__(self, app=None) -> None:
        """Initialize middleware with auth service."""
        if app is not None:
            super().__init__(app)
        self.auth_service = AuthService()

    def extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header.

        Args:
            request: FastAPI request object

        Returns:
            JWT token string

        Raises:
            HTTPException: 401 if Authorization header is missing or invalid
        """
        authorization = request.headers.get("authorization")

        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )

        # Parse "Bearer <token>" format
        parts = authorization.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected: Bearer <token>",
            )

        token = parts[1].strip()

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty token in Authorization header",
            )

        return token

    def authenticate(self, request: Request) -> None:
        """Authenticate request and set vendor context in request.state.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: 401 if token is invalid, expired, or wrong type
        """
        try:
            # Extract token
            token = self.extract_token(request)

            # Validate token (must be ACCESS token, not REFRESH)
            payload = self.auth_service.validate_token(
                token=token,
                expected_type=TokenType.ACCESS,
            )

            # Extract claims
            vendor_id_str = payload.get("vendor_id")
            email = payload.get("email")

            if not vendor_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing vendor_id claim",
                )

            # Set vendor context in request state
            request.state.vendor_id = UUID(vendor_id_str)
            request.state.email = email

        except TokenExpiredError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token expired: {str(e)}",
            ) from e

        except (InvalidTokenError, InvalidTokenTypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            ) from e

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid vendor_id format: {str(e)}",
            ) from e

    async def authenticate_and_set_rls_context(
        self,
        request: Request,
    ) -> None:
        """Authenticate request and set PostgreSQL RLS session variable.

        This method:
        1. Authenticates the request (validates JWT, sets request.state)
        2. Sets PostgreSQL session variable app.current_vendor_id for RLS

        Args:
            request: FastAPI request object with db session in request.state.db

        Raises:
            HTTPException: 401 if authentication fails
        """
        # Authenticate and set request.state
        self.authenticate(request)

        # Set PostgreSQL session variable for RLS
        if hasattr(request.state, "db"):
            db_session = request.state.db
            vendor_id = request.state.vendor_id

            # Set app.current_vendor_id session variable for RLS policies
            db_session.execute(
                text("SET app.current_vendor_id = :vendor_id"),
                {"vendor_id": str(vendor_id)},
            )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request through middleware pipeline.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response from next handler

        Raises:
            HTTPException: 401 if authentication fails
        """
        # Authenticate request
        self.authenticate(request)

        # Continue to next middleware/handler
        response = await call_next(request)

        return response


def get_current_vendor(request: Request) -> UUID:
    """FastAPI dependency to get current authenticated vendor ID.

    Usage in route handlers:
        @router.get("/products")
        def list_products(
            vendor_id: UUID = Depends(get_current_vendor),
        ):
            # vendor_id is authenticated vendor's UUID
            ...

    Args:
        request: FastAPI request object (injected by FastAPI)

    Returns:
        Authenticated vendor's UUID

    Raises:
        HTTPException: 401 if request is not authenticated
    """
    if not hasattr(request.state, "vendor_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return request.state.vendor_id


def get_current_email(request: Request) -> str:
    """FastAPI dependency to get current authenticated vendor email.

    Usage in route handlers:
        @router.get("/profile")
        def get_profile(
            email: str = Depends(get_current_email),
        ):
            # email is authenticated vendor's email
            ...

    Args:
        request: FastAPI request object (injected by FastAPI)

    Returns:
        Authenticated vendor's email

    Raises:
        HTTPException: 401 if request is not authenticated
    """
    if not hasattr(request.state, "email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return request.state.email
