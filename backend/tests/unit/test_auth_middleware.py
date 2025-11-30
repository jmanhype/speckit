"""Unit tests for authentication middleware.

Tests MUST fail before implementation (TDD).
"""
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from fastapi import Request, HTTPException, status
from starlette.datastructures import Headers

# Module under test - will be implemented in T021
from src.middleware.auth import AuthMiddleware, get_current_vendor


class TestAuthMiddlewareTokenExtraction:
    """Test JWT token extraction from Authorization header."""

    def test_extract_token_from_bearer_header(self) -> None:
        """Extract token from 'Bearer <token>' Authorization header."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

        request = self._create_request_with_auth_header(f"Bearer {token}")

        auth_middleware = AuthMiddleware()
        extracted_token = auth_middleware.extract_token(request)

        assert extracted_token == token

    def test_extract_token_ignores_case(self) -> None:
        """Bearer keyword should be case-insensitive."""
        token = "test.token.signature"

        # Test various casings
        for bearer_prefix in ["Bearer", "bearer", "BEARER", "BeArEr"]:
            request = self._create_request_with_auth_header(f"{bearer_prefix} {token}")
            auth_middleware = AuthMiddleware()
            extracted_token = auth_middleware.extract_token(request)
            assert extracted_token == token

    def test_missing_authorization_header_raises_401(self) -> None:
        """Missing Authorization header should raise 401 Unauthorized."""
        request = self._create_request_with_auth_header(None)

        auth_middleware = AuthMiddleware()

        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.extract_token(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "authorization header" in str(exc_info.value.detail).lower()

    def test_invalid_authorization_format_raises_401(self) -> None:
        """Authorization header without 'Bearer' prefix should raise 401."""
        invalid_headers = [
            "just-a-token",
            "Basic dXNlcjpwYXNz",  # Basic auth instead of Bearer
            "Bearer",  # Missing token
            "Bearer  ",  # Only whitespace after Bearer
        ]

        auth_middleware = AuthMiddleware()

        for invalid_header in invalid_headers:
            request = self._create_request_with_auth_header(invalid_header)

            with pytest.raises(HTTPException) as exc_info:
                auth_middleware.extract_token(request)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def _create_request_with_auth_header(self, auth_value: str | None) -> Request:
        """Helper to create mock request with Authorization header."""
        from starlette.datastructures import Headers
        from unittest.mock import Mock

        mock_request = Mock(spec=Request)

        if auth_value is not None:
            mock_request.headers = Headers({"authorization": auth_value})
        else:
            mock_request.headers = Headers({})

        return mock_request


class TestAuthMiddlewareTokenValidation:
    """Test JWT token validation in middleware."""

    def test_valid_token_sets_vendor_id_in_request_state(self) -> None:
        """Valid token should set vendor_id in request.state."""
        from src.services.auth_service import AuthService

        vendor_id = uuid4()
        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="vendor@example.com",
        )

        request = self._create_request_with_token(token)
        auth_middleware = AuthMiddleware()

        # Process the request
        auth_middleware.authenticate(request)

        # Verify vendor_id is set in request state
        assert hasattr(request.state, "vendor_id")
        assert request.state.vendor_id == vendor_id

    def test_valid_token_sets_email_in_request_state(self) -> None:
        """Valid token should set email in request.state."""
        from src.services.auth_service import AuthService

        vendor_id = uuid4()
        email = "vendor@farmersmarket.com"

        auth_service = AuthService()
        token = auth_service.generate_access_token(vendor_id=vendor_id, email=email)

        request = self._create_request_with_token(token)
        auth_middleware = AuthMiddleware()

        auth_middleware.authenticate(request)

        assert hasattr(request.state, "email")
        assert request.state.email == email

    def test_expired_token_raises_401(self) -> None:
        """Expired token should raise 401 Unauthorized."""
        from src.services.auth_service import AuthService
        from freezegun import freeze_time

        vendor_id = uuid4()
        auth_service = AuthService()

        # Generate token at specific time
        with freeze_time("2025-01-15 12:00:00"):
            token = auth_service.generate_access_token(
                vendor_id=vendor_id,
                email="test@example.com",
            )

        # Try to use it 16 minutes later (expires in 15 min)
        with freeze_time("2025-01-15 12:16:00"):
            request = self._create_request_with_token(token)
            auth_middleware = AuthMiddleware()

            with pytest.raises(HTTPException) as exc_info:
                auth_middleware.authenticate(request)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "expired" in str(exc_info.value.detail).lower()

    def test_invalid_token_raises_401(self) -> None:
        """Invalid token should raise 401 Unauthorized."""
        invalid_tokens = [
            "invalid.token.signature",
            "not-a-jwt",
            "",
            "header.payload.invalid_signature",
        ]

        auth_middleware = AuthMiddleware()

        for invalid_token in invalid_tokens:
            request = self._create_request_with_token(invalid_token)

            with pytest.raises(HTTPException) as exc_info:
                auth_middleware.authenticate(request)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_raises_401(self) -> None:
        """Refresh token should not be accepted for authentication."""
        from src.services.auth_service import AuthService

        vendor_id = uuid4()
        auth_service = AuthService()

        # Generate refresh token (not access token)
        refresh_token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        request = self._create_request_with_token(refresh_token)
        auth_middleware = AuthMiddleware()

        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.authenticate(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "token" in str(exc_info.value.detail).lower()

    def _create_request_with_token(self, token: str) -> Request:
        """Helper to create mock request with Bearer token."""
        from unittest.mock import Mock

        mock_request = Mock(spec=Request)
        mock_request.headers = Headers({"authorization": f"Bearer {token}"})
        mock_request.state = Mock()

        return mock_request


class TestAuthMiddlewareRowLevelSecurity:
    """Test RLS (Row-Level Security) context setting."""

    @pytest.mark.asyncio
    async def test_sets_postgresql_session_variable(
        self,
        db_session,
    ) -> None:
        """Middleware should set app.current_vendor_id session variable."""
        from src.services.auth_service import AuthService
        from sqlalchemy import text

        vendor_id = uuid4()
        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="vendor@example.com",
        )

        request = self._create_request_with_token_and_db(token, db_session)
        auth_middleware = AuthMiddleware()

        # Authenticate request (should set PostgreSQL session variable)
        await auth_middleware.authenticate_and_set_rls_context(request)

        # Verify session variable is set in PostgreSQL
        result = db_session.execute(
            text("SELECT current_setting('app.current_vendor_id', true)")
        )
        session_vendor_id = result.scalar()

        assert session_vendor_id == str(vendor_id)

    @pytest.mark.asyncio
    async def test_rls_isolates_vendor_data(self, db_session) -> None:
        """RLS policies should isolate vendor data."""
        from src.services.auth_service import AuthService
        from src.models.vendor import Vendor

        # Create two vendors
        vendor_1_id = uuid4()
        vendor_2_id = uuid4()

        vendor_1 = Vendor(
            id=vendor_1_id,
            email="vendor1@example.com",
            password_hash="hash1",
            business_name="Vendor 1",
        )
        vendor_2 = Vendor(
            id=vendor_2_id,
            email="vendor2@example.com",
            password_hash="hash2",
            business_name="Vendor 2",
        )

        db_session.add_all([vendor_1, vendor_2])
        db_session.commit()

        # Authenticate as vendor_1
        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_1_id,
            email="vendor1@example.com",
        )

        request = self._create_request_with_token_and_db(token, db_session)
        auth_middleware = AuthMiddleware()

        await auth_middleware.authenticate_and_set_rls_context(request)

        # Query vendors table (RLS should only return vendor_1)
        vendors = db_session.query(Vendor).all()

        assert len(vendors) == 1
        assert vendors[0].id == vendor_1_id

    def _create_request_with_token_and_db(self, token: str, db_session) -> Request:
        """Helper to create mock request with token and database session."""
        from unittest.mock import Mock

        mock_request = Mock(spec=Request)
        mock_request.headers = Headers({"authorization": f"Bearer {token}"})
        mock_request.state = Mock()
        mock_request.state.db = db_session

        return mock_request


class TestGetCurrentVendorDependency:
    """Test FastAPI dependency for getting current authenticated vendor."""

    def test_get_current_vendor_returns_vendor_id(self) -> None:
        """get_current_vendor dependency should return vendor_id from request state."""
        vendor_id = uuid4()

        # Create request with vendor_id in state
        request = self._create_request_with_vendor_id(vendor_id)

        # Call dependency
        result = get_current_vendor(request)

        assert result == vendor_id

    def test_get_current_vendor_without_auth_raises_401(self) -> None:
        """get_current_vendor without authenticated request should raise 401."""
        # Create request without vendor_id in state
        request = self._create_request_with_vendor_id(None)

        with pytest.raises(HTTPException) as exc_info:
            get_current_vendor(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def _create_request_with_vendor_id(self, vendor_id: UUID | None) -> Request:
        """Helper to create mock request with vendor_id in state."""
        from unittest.mock import Mock

        mock_request = Mock(spec=Request)
        mock_request.state = Mock()

        if vendor_id is not None:
            mock_request.state.vendor_id = vendor_id
        else:
            # Simulate missing vendor_id attribute
            del mock_request.state.vendor_id

        return mock_request


class TestAuthMiddlewareIntegration:
    """Integration tests for auth middleware in request pipeline."""

    @pytest.mark.asyncio
    async def test_middleware_processes_request_successfully(self) -> None:
        """Middleware should process valid authenticated request."""
        from src.services.auth_service import AuthService
        from starlette.responses import JSONResponse

        vendor_id = uuid4()
        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="vendor@example.com",
        )

        # Create mock request
        from unittest.mock import Mock, AsyncMock

        request = Mock(spec=Request)
        request.headers = Headers({"authorization": f"Bearer {token}"})
        request.state = Mock()

        # Create middleware with mock call_next
        auth_middleware = AuthMiddleware()

        async def mock_call_next(req):
            return JSONResponse({"vendor_id": str(req.state.vendor_id)})

        # Process request through middleware
        response = await auth_middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_rejects_unauthenticated_request(self) -> None:
        """Middleware should reject request without valid token."""
        from unittest.mock import Mock

        request = Mock(spec=Request)
        request.headers = Headers({})  # No Authorization header
        request.state = Mock()

        auth_middleware = AuthMiddleware()

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.dispatch(request, lambda req: None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
