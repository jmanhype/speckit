"""SquareToken model for OAuth integration.

Stores Square OAuth access tokens and refresh tokens for vendors.
Tokens are encrypted at rest for security.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantModel


class SquareToken(TenantModel):
    """
    SquareToken stores encrypted Square OAuth credentials.

    Security:
    - Tokens are encrypted using Fernet (symmetric encryption)
    - One token per vendor (unique constraint on vendor_id)
    - Automatic token refresh before expiration
    """

    __tablename__ = "square_tokens"

    # Encrypted tokens (stored as encrypted strings)
    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted Square access token",
    )

    refresh_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted Square refresh token",
    )

    # Token metadata
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When access token expires (UTC)",
    )

    merchant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Square merchant ID",
    )

    # OAuth scopes granted
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Space-separated OAuth scopes",
    )

    # Connection status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether token is currently active",
    )

    last_refresh_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time token was refreshed",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SquareToken(vendor_id={self.vendor_id}, "
            f"merchant_id={self.merchant_id}, is_active={self.is_active})>"
        )
