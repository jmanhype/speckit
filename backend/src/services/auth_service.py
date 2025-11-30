"""JWT token generation and validation service.

Implements secure JWT-based authentication with:
- Access tokens (15 minute expiration)
- Refresh tokens (7 day expiration)
- Token type validation
- Signature verification using HS256
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any
from uuid import UUID

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from src.config import settings


class TokenType(Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenExpiredError(Exception):
    """Raised when token has expired."""

    pass


class InvalidTokenError(Exception):
    """Raised when token signature or structure is invalid."""

    pass


class InvalidTokenTypeError(Exception):
    """Raised when token type doesn't match expected type."""

    pass


class AuthService:
    """JWT token generation and validation service.

    Handles:
    - Generating access tokens (15 min expiration) with vendor_id and email
    - Generating refresh tokens (7 day expiration) with vendor_id only
    - Validating tokens with signature verification
    - Extracting claims from validated tokens
    - Token refresh workflow
    """

    # Token expiration durations
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    # JWT algorithm
    ALGORITHM = "HS256"

    def __init__(self) -> None:
        """Initialize auth service with secret key from config."""
        self.secret_key = settings.secret_key

        # Validate secret key length (minimum 32 bytes for HS256)
        if len(self.secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")

    def generate_access_token(
        self,
        vendor_id: UUID,
        email: str,
    ) -> str:
        """Generate access token with vendor claims.

        Args:
            vendor_id: Vendor UUID for tenant isolation
            email: Vendor email address

        Returns:
            Encoded JWT access token (expires in 15 minutes)
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload: Dict[str, Any] = {
            "vendor_id": str(vendor_id),
            "email": email,
            "token_type": TokenType.ACCESS.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }

        return jwt.encode(
            claims=payload,
            key=self.secret_key,
            algorithm=self.ALGORITHM,
        )

    def generate_refresh_token(self, vendor_id: UUID) -> str:
        """Generate refresh token with minimal claims.

        Refresh tokens only contain vendor_id (not email) for security.

        Args:
            vendor_id: Vendor UUID

        Returns:
            Encoded JWT refresh token (expires in 7 days)
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        payload: Dict[str, Any] = {
            "vendor_id": str(vendor_id),
            "token_type": TokenType.REFRESH.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }

        return jwt.encode(
            claims=payload,
            key=self.secret_key,
            algorithm=self.ALGORITHM,
        )

    def validate_token(
        self,
        token: str,
        expected_type: TokenType,
    ) -> Dict[str, Any]:
        """Validate JWT token and verify token type.

        Args:
            token: JWT token string
            expected_type: Expected token type (ACCESS or REFRESH)

        Returns:
            Decoded payload dictionary

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token signature or structure is invalid
            InvalidTokenTypeError: Token type doesn't match expected type
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token=token,
                key=self.secret_key,
                algorithms=[self.ALGORITHM],
            )

            # Verify token type matches expected
            token_type = payload.get("token_type")
            if token_type != expected_type.value:
                raise InvalidTokenTypeError(
                    f"Expected {expected_type.value} token, got {token_type}"
                )

            return payload

        except ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e

        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}") from e

    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """Decode token WITHOUT signature verification.

        WARNING: Only use for testing! Does not validate signature or expiration.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dictionary (unverified)
        """
        try:
            return jwt.decode(
                token=token,
                key=self.secret_key,
                algorithms=[self.ALGORITHM],
                options={"verify_signature": False, "verify_exp": False},
            )
        except JWTError as e:
            raise InvalidTokenError(f"Malformed token: {str(e)}") from e

    def get_vendor_id_from_token(self, token: str) -> UUID:
        """Extract vendor_id from token.

        Validates token and extracts vendor_id claim.
        Works with both access and refresh tokens.

        Args:
            token: JWT token string

        Returns:
            Vendor UUID

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token is invalid
        """
        # Decode without type checking (works for both access and refresh)
        try:
            payload = jwt.decode(
                token=token,
                key=self.secret_key,
                algorithms=[self.ALGORITHM],
            )

            vendor_id_str = payload.get("vendor_id")
            if not vendor_id_str:
                raise InvalidTokenError("Token missing vendor_id claim")

            return UUID(vendor_id_str)

        except ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e

        except (JWTError, ValueError) as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}") from e

    def refresh_access_token(
        self,
        refresh_token: str,
        email: str,
    ) -> str:
        """Generate new access token from valid refresh token.

        Args:
            refresh_token: Valid refresh token
            email: Vendor email for new access token

        Returns:
            New access token

        Raises:
            TokenExpiredError: Refresh token has expired
            InvalidTokenError: Refresh token is invalid
            InvalidTokenTypeError: Token is not a refresh token
        """
        # Validate refresh token
        payload = self.validate_token(
            token=refresh_token,
            expected_type=TokenType.REFRESH,
        )

        # Extract vendor_id and generate new access token
        vendor_id = UUID(payload["vendor_id"])

        return self.generate_access_token(
            vendor_id=vendor_id,
            email=email,
        )
