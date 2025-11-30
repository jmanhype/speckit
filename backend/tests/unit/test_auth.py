"""Unit tests for JWT token generation and validation.

Tests MUST fail before implementation (TDD).
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from freezegun import freeze_time

# Module under test - will be implemented in T019
from src.services.auth_service import AuthService, TokenType


class TestJWTTokenGeneration:
    """Test JWT access and refresh token generation."""

    def test_generate_access_token_with_vendor_claims(self) -> None:
        """Generate access token with vendor_id and email claims."""
        vendor_id = uuid4()
        email = "vendor@example.com"

        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email=email,
        )

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Token should have 3 parts (header.payload.signature)
        assert token.count(".") == 2

    def test_generate_access_token_includes_expiration(self) -> None:
        """Access token should expire in 15 minutes."""
        vendor_id = uuid4()

        with freeze_time("2025-01-15 12:00:00"):
            auth_service = AuthService()
            token = auth_service.generate_access_token(
                vendor_id=vendor_id,
                email="test@example.com",
            )

            # Decode without verification to check expiration
            payload = auth_service.decode_token_unsafe(token)

            expected_exp = datetime(2025, 1, 15, 12, 15, 0)
            assert payload["exp"] == int(expected_exp.timestamp())

    def test_generate_refresh_token_with_vendor_id(self) -> None:
        """Generate refresh token with vendor_id claim."""
        vendor_id = uuid4()

        auth_service = AuthService()
        token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_generate_refresh_token_expires_in_7_days(self) -> None:
        """Refresh token should expire in 7 days."""
        vendor_id = uuid4()

        with freeze_time("2025-01-15 12:00:00"):
            auth_service = AuthService()
            token = auth_service.generate_refresh_token(vendor_id=vendor_id)

            payload = auth_service.decode_token_unsafe(token)

            expected_exp = datetime(2025, 1, 22, 12, 0, 0)
            assert payload["exp"] == int(expected_exp.timestamp())

    def test_generate_tokens_include_token_type(self) -> None:
        """Access and refresh tokens should include token_type claim."""
        vendor_id = uuid4()
        auth_service = AuthService()

        access_token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="test@example.com",
        )
        refresh_token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        access_payload = auth_service.decode_token_unsafe(access_token)
        refresh_payload = auth_service.decode_token_unsafe(refresh_token)

        assert access_payload["token_type"] == TokenType.ACCESS.value
        assert refresh_payload["token_type"] == TokenType.REFRESH.value


class TestJWTTokenValidation:
    """Test JWT token validation and verification."""

    def test_validate_access_token_success(self) -> None:
        """Valid access token should be validated successfully."""
        vendor_id = uuid4()
        email = "vendor@example.com"

        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email=email,
        )

        # Validation should succeed and return payload
        payload = auth_service.validate_token(
            token=token,
            expected_type=TokenType.ACCESS,
        )

        assert payload["vendor_id"] == str(vendor_id)
        assert payload["email"] == email
        assert payload["token_type"] == TokenType.ACCESS.value

    def test_validate_refresh_token_success(self) -> None:
        """Valid refresh token should be validated successfully."""
        vendor_id = uuid4()

        auth_service = AuthService()
        token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        payload = auth_service.validate_token(
            token=token,
            expected_type=TokenType.REFRESH,
        )

        assert payload["vendor_id"] == str(vendor_id)
        assert payload["token_type"] == TokenType.REFRESH.value

    def test_validate_expired_token_raises_error(self) -> None:
        """Expired token should raise TokenExpiredError."""
        from src.services.auth_service import TokenExpiredError

        vendor_id = uuid4()
        auth_service = AuthService()

        # Generate token at specific time
        with freeze_time("2025-01-15 12:00:00"):
            token = auth_service.generate_access_token(
                vendor_id=vendor_id,
                email="test@example.com",
            )

        # Validate 16 minutes later (access tokens expire in 15 min)
        with freeze_time("2025-01-15 12:16:00"):
            with pytest.raises(TokenExpiredError) as exc_info:
                auth_service.validate_token(
                    token=token,
                    expected_type=TokenType.ACCESS,
                )

            assert "expired" in str(exc_info.value).lower()

    def test_validate_token_with_invalid_signature_raises_error(self) -> None:
        """Token with invalid signature should raise InvalidTokenError."""
        from src.services.auth_service import InvalidTokenError

        auth_service = AuthService()

        # Generate valid token
        vendor_id = uuid4()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="test@example.com",
        )

        # Tamper with signature (last part)
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"

        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.validate_token(
                token=tampered_token,
                expected_type=TokenType.ACCESS,
            )

        assert "invalid" in str(exc_info.value).lower()

    def test_validate_malformed_token_raises_error(self) -> None:
        """Malformed token should raise InvalidTokenError."""
        from src.services.auth_service import InvalidTokenError

        auth_service = AuthService()

        malformed_tokens = [
            "not.a.valid.jwt.token",
            "only_one_part",
            "two.parts",
            "",
            "header.payload.",  # Missing signature
        ]

        for malformed_token in malformed_tokens:
            with pytest.raises(InvalidTokenError):
                auth_service.validate_token(
                    token=malformed_token,
                    expected_type=TokenType.ACCESS,
                )

    def test_validate_access_token_as_refresh_raises_error(self) -> None:
        """Validating access token as refresh token should raise error."""
        from src.services.auth_service import InvalidTokenTypeError

        vendor_id = uuid4()
        auth_service = AuthService()

        access_token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="test@example.com",
        )

        # Try to validate access token as refresh token
        with pytest.raises(InvalidTokenTypeError) as exc_info:
            auth_service.validate_token(
                token=access_token,
                expected_type=TokenType.REFRESH,
            )

        assert "token_type" in str(exc_info.value).lower()

    def test_validate_refresh_token_as_access_raises_error(self) -> None:
        """Validating refresh token as access token should raise error."""
        from src.services.auth_service import InvalidTokenTypeError

        vendor_id = uuid4()
        auth_service = AuthService()

        refresh_token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        # Try to validate refresh token as access token
        with pytest.raises(InvalidTokenTypeError):
            auth_service.validate_token(
                token=refresh_token,
                expected_type=TokenType.ACCESS,
            )


class TestTokenPayloadExtraction:
    """Test extraction of claims from validated tokens."""

    def test_extract_vendor_id_from_access_token(self) -> None:
        """Extract vendor_id from validated access token."""
        vendor_id = uuid4()
        auth_service = AuthService()

        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="test@example.com",
        )

        extracted_vendor_id = auth_service.get_vendor_id_from_token(token)

        assert extracted_vendor_id == vendor_id

    def test_extract_vendor_id_from_refresh_token(self) -> None:
        """Extract vendor_id from validated refresh token."""
        vendor_id = uuid4()
        auth_service = AuthService()

        token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        extracted_vendor_id = auth_service.get_vendor_id_from_token(token)

        assert extracted_vendor_id == vendor_id

    def test_extract_email_from_access_token(self) -> None:
        """Extract email from access token payload."""
        vendor_id = uuid4()
        email = "vendor@farmersmarket.com"

        auth_service = AuthService()
        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email=email,
        )

        payload = auth_service.validate_token(
            token=token,
            expected_type=TokenType.ACCESS,
        )

        assert payload["email"] == email

    def test_refresh_token_does_not_include_email(self) -> None:
        """Refresh tokens should only contain vendor_id, not email."""
        vendor_id = uuid4()
        auth_service = AuthService()

        token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        payload = auth_service.validate_token(
            token=token,
            expected_type=TokenType.REFRESH,
        )

        assert "vendor_id" in payload
        assert "email" not in payload


class TestTokenSecurityRequirements:
    """Test security requirements for JWT tokens."""

    def test_tokens_use_hs256_algorithm(self) -> None:
        """Tokens should use HS256 algorithm for signing."""
        vendor_id = uuid4()
        auth_service = AuthService()

        token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email="test@example.com",
        )

        # Decode header to check algorithm
        import base64
        import json

        header = token.split(".")[0]
        # Add padding if needed
        header += "=" * (4 - len(header) % 4)
        decoded_header = json.loads(base64.urlsafe_b64decode(header))

        assert decoded_header["alg"] == "HS256"

    def test_secret_key_from_config(self) -> None:
        """AuthService should use secret key from config."""
        from src.config import settings

        auth_service = AuthService()

        # Secret key should be loaded from settings
        assert auth_service.secret_key == settings.secret_key
        assert len(auth_service.secret_key) >= 32  # Minimum key length

    def test_tokens_include_issued_at_claim(self) -> None:
        """Tokens should include 'iat' (issued at) claim."""
        vendor_id = uuid4()

        with freeze_time("2025-01-15 12:00:00"):
            auth_service = AuthService()
            token = auth_service.generate_access_token(
                vendor_id=vendor_id,
                email="test@example.com",
            )

            payload = auth_service.decode_token_unsafe(token)

            expected_iat = int(datetime(2025, 1, 15, 12, 0, 0).timestamp())
            assert payload["iat"] == expected_iat

    def test_different_vendors_get_different_tokens(self) -> None:
        """Tokens for different vendors should be unique."""
        vendor_id_1 = uuid4()
        vendor_id_2 = uuid4()

        auth_service = AuthService()

        token_1 = auth_service.generate_access_token(
            vendor_id=vendor_id_1,
            email="vendor1@example.com",
        )
        token_2 = auth_service.generate_access_token(
            vendor_id=vendor_id_2,
            email="vendor2@example.com",
        )

        assert token_1 != token_2


class TestTokenRefreshWorkflow:
    """Test refresh token workflow for token rotation."""

    def test_refresh_access_token_from_valid_refresh_token(self) -> None:
        """Generate new access token from valid refresh token."""
        vendor_id = uuid4()
        email = "vendor@example.com"

        auth_service = AuthService()

        # Generate initial refresh token
        refresh_token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        # Use refresh token to generate new access token
        new_access_token = auth_service.refresh_access_token(
            refresh_token=refresh_token,
            email=email,
        )

        # Validate new access token
        payload = auth_service.validate_token(
            token=new_access_token,
            expected_type=TokenType.ACCESS,
        )

        assert payload["vendor_id"] == str(vendor_id)
        assert payload["email"] == email

    def test_refresh_access_token_with_expired_refresh_token_raises_error(
        self,
    ) -> None:
        """Expired refresh token should not generate new access token."""
        from src.services.auth_service import TokenExpiredError

        vendor_id = uuid4()
        auth_service = AuthService()

        # Generate refresh token
        with freeze_time("2025-01-15 12:00:00"):
            refresh_token = auth_service.generate_refresh_token(vendor_id=vendor_id)

        # Try to use it 8 days later (expires in 7 days)
        with freeze_time("2025-01-23 12:00:00"):
            with pytest.raises(TokenExpiredError):
                auth_service.refresh_access_token(
                    refresh_token=refresh_token,
                    email="vendor@example.com",
                )

    def test_cannot_use_access_token_for_refresh(self) -> None:
        """Access tokens cannot be used to refresh."""
        from src.services.auth_service import InvalidTokenTypeError

        vendor_id = uuid4()
        email = "vendor@example.com"

        auth_service = AuthService()

        # Generate access token
        access_token = auth_service.generate_access_token(
            vendor_id=vendor_id,
            email=email,
        )

        # Try to use access token for refresh
        with pytest.raises(InvalidTokenTypeError):
            auth_service.refresh_access_token(
                refresh_token=access_token,
                email=email,
            )
