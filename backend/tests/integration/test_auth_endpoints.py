"""Integration tests for authentication endpoints.

Tests MUST fail before implementation (TDD).
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

# Modules under test - will be implemented in T023-T024
from src.main import app
from src.models.vendor import Vendor


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestLoginEndpoint:
    """Integration tests for POST /auth/login endpoint."""

    def test_login_success_returns_tokens(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Successful login returns access_token and refresh_token."""
        # Create vendor with known password
        password = "SecurePassword123!"
        password_hash = pwd_context.hash(password)

        vendor = Vendor(
            id=uuid4(),
            email="vendor@example.com",
            password_hash=password_hash,
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Login request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "vendor@example.com",
                "password": password,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

        # Tokens should be non-empty strings
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        assert isinstance(data["refresh_token"], str)
        assert len(data["refresh_token"]) > 0

    def test_login_tokens_are_valid_jwts(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Returned tokens should be valid JWTs that can be validated."""
        from src.services.auth_service import AuthService, TokenType

        # Create vendor
        password = "SecurePassword123!"
        password_hash = pwd_context.hash(password)
        vendor_id = uuid4()

        vendor = Vendor(
            id=vendor_id,
            email="vendor@example.com",
            password_hash=password_hash,
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "vendor@example.com",
                "password": password,
            },
        )

        data = response.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Validate tokens using AuthService
        auth_service = AuthService()

        access_payload = auth_service.validate_token(
            access_token,
            TokenType.ACCESS,
        )
        assert access_payload["vendor_id"] == str(vendor_id)
        assert access_payload["email"] == "vendor@example.com"

        refresh_payload = auth_service.validate_token(
            refresh_token,
            TokenType.REFRESH,
        )
        assert refresh_payload["vendor_id"] == str(vendor_id)

    def test_login_with_wrong_password_returns_401(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Login with wrong password returns 401 Unauthorized."""
        # Create vendor
        password = "CorrectPassword123!"
        password_hash = pwd_context.hash(password)

        vendor = Vendor(
            id=uuid4(),
            email="vendor@example.com",
            password_hash=password_hash,
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "vendor@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "incorrect" in data["detail"].lower()

    def test_login_with_nonexistent_email_returns_401(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Login with non-existent email returns 401 Unauthorized."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        # Should not reveal whether email exists (security best practice)
        assert "invalid" in data["detail"].lower() or "incorrect" in data["detail"].lower()

    def test_login_with_missing_email_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Login request missing email returns 422 Validation Error."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 422

    def test_login_with_missing_password_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Login request missing password returns 422 Validation Error."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "vendor@example.com",
            },
        )

        assert response.status_code == 422

    def test_login_with_invalid_email_format_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Login with invalid email format returns 422 Validation Error."""
        invalid_emails = [
            "not-an-email",
            "missing@domain",
            "@missing-local.com",
            "spaces in@email.com",
        ]

        for invalid_email in invalid_emails:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": invalid_email,
                    "password": "SomePassword123!",
                },
            )

            assert response.status_code == 422

    def test_login_returns_vendor_info(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Login response should include basic vendor information."""
        # Create vendor
        password = "SecurePassword123!"
        password_hash = pwd_context.hash(password)
        vendor_id = uuid4()

        vendor = Vendor(
            id=vendor_id,
            email="vendor@example.com",
            password_hash=password_hash,
            business_name="Happy Farm",
            subscription_tier="mvp",
            subscription_status="active",
        )
        db_session.add(vendor)
        db_session.commit()

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "vendor@example.com",
                "password": password,
            },
        )

        data = response.json()

        # Should include vendor info
        assert "vendor" in data
        assert data["vendor"]["id"] == str(vendor_id)
        assert data["vendor"]["email"] == "vendor@example.com"
        assert data["vendor"]["business_name"] == "Happy Farm"
        assert data["vendor"]["subscription_tier"] == "mvp"
        assert data["vendor"]["subscription_status"] == "active"

        # Should NOT include password hash
        assert "password_hash" not in data["vendor"]


class TestRefreshTokenEndpoint:
    """Integration tests for POST /auth/refresh endpoint."""

    def test_refresh_token_returns_new_access_token(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Valid refresh token returns new access token."""
        from src.services.auth_service import AuthService

        # Create vendor
        password = "SecurePassword123!"
        password_hash = pwd_context.hash(password)
        vendor_id = uuid4()
        email = "vendor@example.com"

        vendor = Vendor(
            id=vendor_id,
            email=email,
            password_hash=password_hash,
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Generate refresh token
        auth_service = AuthService()
        refresh_token = auth_service.generate_refresh_token(vendor_id)

        # Request new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": refresh_token,
                "email": email,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

        # New access token should be valid
        new_access_token = data["access_token"]
        from src.services.auth_service import TokenType

        payload = auth_service.validate_token(new_access_token, TokenType.ACCESS)
        assert payload["vendor_id"] == str(vendor_id)
        assert payload["email"] == email

    def test_refresh_with_expired_token_returns_401(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Expired refresh token returns 401 Unauthorized."""
        from src.services.auth_service import AuthService
        from freezegun import freeze_time

        # Create vendor
        vendor_id = uuid4()
        vendor = Vendor(
            id=vendor_id,
            email="vendor@example.com",
            password_hash="hash",
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Generate refresh token
        auth_service = AuthService()

        with freeze_time("2025-01-15 12:00:00"):
            refresh_token = auth_service.generate_refresh_token(vendor_id)

        # Try to use it 8 days later (expires in 7 days)
        with freeze_time("2025-01-23 12:00:00"):
            response = client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": refresh_token,
                    "email": "vendor@example.com",
                },
            )

            assert response.status_code == 401

    def test_refresh_with_access_token_returns_401(
        self,
        client: TestClient,
        db_session,
    ) -> None:
        """Using access token for refresh returns 401."""
        from src.services.auth_service import AuthService

        # Create vendor
        vendor_id = uuid4()
        email = "vendor@example.com"

        vendor = Vendor(
            id=vendor_id,
            email=email,
            password_hash="hash",
            business_name="Test Farm",
        )
        db_session.add(vendor)
        db_session.commit()

        # Generate ACCESS token (not refresh token)
        auth_service = AuthService()
        access_token = auth_service.generate_access_token(vendor_id, email)

        # Try to use access token for refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": access_token,  # Wrong token type!
                "email": email,
            },
        )

        assert response.status_code == 401

    def test_refresh_with_invalid_token_returns_401(
        self,
        client: TestClient,
    ) -> None:
        """Invalid refresh token returns 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid.token.signature",
                "email": "vendor@example.com",
            },
        )

        assert response.status_code == 401


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)
