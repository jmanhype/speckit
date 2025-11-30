"""Vendor model - multi-tenant root entity."""
from typing import Optional

from sqlalchemy import Boolean, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class Vendor(BaseModel):
    """
    Vendor represents a farmers market seller (multi-tenant root).

    All data in the system is scoped to a vendor via Row-Level Security (RLS).
    """

    __tablename__ = "vendors"

    # Authentication & Contact
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Vendor's login email (unique)",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Public-facing business name",
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Contact phone number",
    )

    # Subscription
    subscription_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="mvp",
        comment="Pricing tier: 'mvp' ($29/month) or 'multi_location' ($79/month)",
    )

    subscription_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="trial",
        comment="Billing status: 'trial', 'active', 'suspended', 'cancelled'",
    )

    # Square Integration
    square_connected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Quick check if Square OAuth completed",
    )

    square_merchant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square merchant ID for reference",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "subscription_tier IN ('mvp', 'multi_location')",
            name="check_subscription_tier",
        ),
        CheckConstraint(
            "subscription_status IN ('trial', 'active', 'suspended', 'cancelled')",
            name="check_subscription_status",
        ),
    )

    # Relationships (lazy-loaded to avoid circular imports)
    # products = relationship("Product", back_populates="vendor", cascade="all, delete-orphan")
    # square_token = relationship("SquareToken", back_populates="vendor", uselist=False)
    # subscriptions = relationship("Subscription", back_populates="vendor")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Vendor(id={self.id}, email={self.email}, business_name={self.business_name})>"
