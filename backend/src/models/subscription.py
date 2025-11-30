"""
Subscription and billing models

Supports multiple subscription tiers with usage-based billing.
Integrates with Stripe for payment processing.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, String, Boolean, DateTime, Numeric, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TenantModel


class SubscriptionTier(str, Enum):
    """Subscription tier levels"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"


class Subscription(TenantModel):
    """
    Vendor subscription record

    Tracks subscription tier, billing cycle, and Stripe integration.
    """
    __tablename__ = "subscriptions"

    # Stripe IDs
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Subscription details
    tier: Mapped[str] = mapped_column(String(50), default="free", index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)

    # Billing cycle
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Trial
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Usage limits (per month)
    recommendations_limit: Mapped[Optional[int]] = mapped_column(Integer)  # None = unlimited
    products_limit: Mapped[Optional[int]] = mapped_column(Integer)
    venues_limit: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index('ix_subscriptions_vendor_tier', 'vendor_id', 'tier'),
        Index('ix_subscriptions_vendor_status', 'vendor_id', 'status'),
        Index('ix_subscriptions_period_end', 'current_period_end'),
        TenantModel.__table_args__,
    )

    def is_active(self) -> bool:
        """Check if subscription is active"""
        return self.status == "active"

    def is_trialing(self) -> bool:
        """Check if subscription is in trial"""
        return self.status == "trialing"

    def has_reached_limit(self, limit_type: str, current_usage: int) -> bool:
        """
        Check if usage limit has been reached

        Args:
            limit_type: "recommendations", "products", or "venues"
            current_usage: Current usage count

        Returns:
            True if limit reached, False otherwise (or if no limit)
        """
        limit_map = {
            "recommendations": self.recommendations_limit,
            "products": self.products_limit,
            "venues": self.venues_limit,
        }

        limit = limit_map.get(limit_type)
        if limit is None:  # Unlimited
            return False

        return current_usage >= limit

    @staticmethod
    def get_tier_limits(tier: str) -> dict:
        """
        Get usage limits for a subscription tier

        Returns:
            Dictionary with limit values
        """
        limits = {
            "free": {
                "recommendations_limit": 50,
                "products_limit": 20,
                "venues_limit": 2,
                "price_monthly": Decimal("0.00"),
                "price_yearly": Decimal("0.00"),
            },
            "pro": {
                "recommendations_limit": 500,
                "products_limit": 100,
                "venues_limit": 10,
                "price_monthly": Decimal("29.00"),
                "price_yearly": Decimal("290.00"),  # 2 months free
            },
            "enterprise": {
                "recommendations_limit": None,  # Unlimited
                "products_limit": None,
                "venues_limit": None,
                "price_monthly": Decimal("99.00"),
                "price_yearly": Decimal("990.00"),
            },
        }
        return limits.get(tier, limits["free"])


class UsageRecord(TenantModel):
    """
    Tracks usage for billing purposes

    Used for metered billing and usage analytics.
    """
    __tablename__ = "usage_records"

    subscription_id: Mapped[str] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True)

    # Usage type
    usage_type: Mapped[str] = mapped_column(String(50), index=True)  # "recommendations", "products", "api_calls"

    # Usage details
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Billing period
    billing_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    billing_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Stripe metered billing
    stripe_usage_record_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="usage_records")

    # Indexes
    __table_args__ = (
        Index('ix_usage_vendor_type_period', 'vendor_id', 'usage_type', 'billing_period_start'),
        Index('ix_usage_subscription_timestamp', 'subscription_id', 'timestamp'),
        TenantModel.__table_args__,
    )


class Invoice(TenantModel):
    """
    Invoice records for subscription billing

    Synced with Stripe invoices.
    """
    __tablename__ = "invoices"

    subscription_id: Mapped[str] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True)

    # Stripe IDs
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Invoice details
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="usd")

    # Status
    status: Mapped[str] = mapped_column(String(50), index=True)  # "draft", "open", "paid", "void", "uncollectible"
    paid: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Dates
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Invoice PDF
    invoice_pdf_url: Mapped[Optional[str]] = mapped_column(String(500))
    hosted_invoice_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="invoices")

    # Indexes
    __table_args__ = (
        Index('ix_invoices_vendor_status', 'vendor_id', 'status'),
        Index('ix_invoices_vendor_date', 'vendor_id', 'invoice_date'),
        Index('ix_invoices_due_date', 'due_date'),
        TenantModel.__table_args__,
    )


class PaymentMethod(TenantModel):
    """
    Stored payment methods (credit cards, bank accounts)

    Stores Stripe payment method IDs, not actual card details.
    """
    __tablename__ = "payment_methods"

    # Stripe IDs
    stripe_payment_method_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True)

    # Payment method type
    type: Mapped[str] = mapped_column(String(50))  # "card", "bank_account", etc.

    # Card details (last 4 digits, brand only - no sensitive data)
    card_brand: Mapped[Optional[str]] = mapped_column(String(50))  # "visa", "mastercard", etc.
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))
    card_exp_month: Mapped[Optional[int]] = mapped_column(Integer)
    card_exp_year: Mapped[Optional[int]] = mapped_column(Integer)

    # Bank account details (last 4 digits only)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100))
    bank_last4: Mapped[Optional[str]] = mapped_column(String(4))

    # Status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Indexes
    __table_args__ = (
        Index('ix_payment_methods_vendor_default', 'vendor_id', 'is_default'),
        TenantModel.__table_args__,
    )
