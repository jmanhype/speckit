"""Square OAuth service.

Handles Square OAuth 2.0 flow:
1. Generate authorization URL
2. Exchange authorization code for tokens
3. Store encrypted tokens
4. Refresh access tokens
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID
import secrets
import httpx

from sqlalchemy.orm import Session

from src.config import settings
from src.models.square_token import SquareToken
from src.models.vendor import Vendor
from src.services.encryption import encryption_service


class SquareOAuthService:
    """Service for Square OAuth integration."""

    # Square OAuth endpoints
    SQUARE_OAUTH_BASE_URL = "https://connect.squareup.com/oauth2"
    SQUARE_API_BASE_URL = (
        "https://connect.squareupsandbox.com"
        if settings.square_environment == "sandbox"
        else "https://connect.squareup.com"
    )

    # OAuth scopes required for MarketPrep
    REQUIRED_SCOPES = [
        "ITEMS_READ",  # Read catalog items
        "ORDERS_READ",  # Read orders
        "PAYMENTS_READ",  # Read payment history
    ]

    def __init__(self):
        """Initialize Square OAuth service."""
        self.client_id = settings.square_application_id
        self.client_secret = settings.square_application_secret
        self.redirect_uri = settings.square_oauth_redirect_uri

    def generate_authorization_url(self, state: str | None = None) -> Dict[str, str]:
        """Generate Square OAuth authorization URL.

        Args:
            state: Optional CSRF token (generated if not provided)

        Returns:
            Dictionary with 'url' and 'state'
        """
        # Generate CSRF token if not provided
        if state is None:
            state = secrets.token_urlsafe(32)

        # Build authorization URL
        scopes = " ".join(self.REQUIRED_SCOPES)

        params = {
            "client_id": self.client_id,
            "scope": scopes,
            "session": "false",  # Don't use Square's session management
            "state": state,
        }

        # Build URL with query parameters
        url = f"{self.SQUARE_OAUTH_BASE_URL}/authorize"
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{url}?{query_string}"

        return {
            "url": authorization_url,
            "state": state,
        }

    async def exchange_code_for_tokens(
        self,
        authorization_code: str,
        vendor_id: UUID,
        db: Session,
    ) -> SquareToken:
        """Exchange authorization code for access and refresh tokens.

        Args:
            authorization_code: Authorization code from Square callback
            vendor_id: Vendor UUID
            db: Database session

        Returns:
            Created SquareToken model

        Raises:
            HTTPException: If token exchange fails
        """
        from fastapi import HTTPException, status

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.SQUARE_OAUTH_BASE_URL}/token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for tokens: {response.text}",
                )

            token_data = response.json()

        # Extract token information
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_at_str = token_data["expires_at"]  # ISO 8601 format
        merchant_id = token_data["merchant_id"]

        # Parse expiration time
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))

        # Encrypt tokens
        access_token_encrypted = encryption_service.encrypt(access_token)
        refresh_token_encrypted = encryption_service.encrypt(refresh_token)

        # Store or update token in database
        existing_token = (
            db.query(SquareToken).filter(SquareToken.vendor_id == vendor_id).first()
        )

        if existing_token:
            # Update existing token
            existing_token.access_token_encrypted = access_token_encrypted
            existing_token.refresh_token_encrypted = refresh_token_encrypted
            existing_token.expires_at = expires_at
            existing_token.merchant_id = merchant_id
            existing_token.scopes = " ".join(self.REQUIRED_SCOPES)
            existing_token.is_active = True
            existing_token.updated_at = datetime.utcnow()

            square_token = existing_token
        else:
            # Create new token
            square_token = SquareToken(
                vendor_id=vendor_id,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                expires_at=expires_at,
                merchant_id=merchant_id,
                scopes=" ".join(self.REQUIRED_SCOPES),
                is_active=True,
            )
            db.add(square_token)

        # Update vendor's square_connected flag
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if vendor:
            vendor.square_connected = True
            vendor.square_merchant_id = merchant_id

        db.commit()
        db.refresh(square_token)

        return square_token

    async def refresh_access_token(
        self,
        vendor_id: UUID,
        db: Session,
    ) -> str:
        """Refresh Square access token.

        Args:
            vendor_id: Vendor UUID
            db: Database session

        Returns:
            New decrypted access token

        Raises:
            HTTPException: If refresh fails
        """
        from fastapi import HTTPException, status

        # Get existing token
        square_token = (
            db.query(SquareToken).filter(SquareToken.vendor_id == vendor_id).first()
        )

        if not square_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Square token not found",
            )

        # Decrypt refresh token
        refresh_token = encryption_service.decrypt(
            square_token.refresh_token_encrypted
        )

        # Refresh access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.SQUARE_OAUTH_BASE_URL}/token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                # Mark token as inactive
                square_token.is_active = False
                db.commit()

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to refresh token: {response.text}",
                )

            token_data = response.json()

        # Extract new tokens
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token", refresh_token)
        expires_at_str = token_data["expires_at"]

        # Parse expiration
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))

        # Encrypt new tokens
        access_token_encrypted = encryption_service.encrypt(new_access_token)
        refresh_token_encrypted = encryption_service.encrypt(new_refresh_token)

        # Update database
        square_token.access_token_encrypted = access_token_encrypted
        square_token.refresh_token_encrypted = refresh_token_encrypted
        square_token.expires_at = expires_at
        square_token.last_refresh_at = datetime.utcnow()
        square_token.updated_at = datetime.utcnow()

        db.commit()

        return new_access_token

    def get_access_token(
        self,
        vendor_id: UUID,
        db: Session,
    ) -> str:
        """Get decrypted access token for vendor.

        Automatically refreshes if token is expired or about to expire.

        Args:
            vendor_id: Vendor UUID
            db: Database session

        Returns:
            Decrypted access token

        Raises:
            HTTPException: If token not found or refresh fails
        """
        from fastapi import HTTPException, status
        import asyncio

        # Get token from database
        square_token = (
            db.query(SquareToken)
            .filter(
                SquareToken.vendor_id == vendor_id,
                SquareToken.is_active == True,
            )
            .first()
        )

        if not square_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Square not connected. Please connect your Square account.",
            )

        # Check if token is expired or expiring soon (within 1 hour)
        now = datetime.utcnow()
        expiry_buffer = timedelta(hours=1)

        if square_token.expires_at <= (now + expiry_buffer):
            # Token expired or expiring soon - refresh it
            access_token = asyncio.run(
                self.refresh_access_token(vendor_id, db)
            )
            return access_token

        # Decrypt and return current token
        access_token = encryption_service.decrypt(
            square_token.access_token_encrypted
        )

        return access_token


# Global Square OAuth service instance
square_oauth_service = SquareOAuthService()
