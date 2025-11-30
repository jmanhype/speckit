"""Sale model for tracking transactions.

Sales are synced from Square orders/payments.
Used for:
- Sales history analysis
- Recommendation engine training data
- Revenue tracking
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantModel


class Sale(TenantModel):
    """
    Sale represents a completed transaction.

    Synced from Square orders/payments.
    """

    __tablename__ = "sales"

    # Sale Information
    sale_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When sale occurred (UTC)",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total sale amount in USD",
    )

    # Square Integration
    square_order_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        unique=True,
        comment="Square order ID",
    )

    square_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square payment ID",
    )

    square_location_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square location ID",
    )

    # Line Items (stored as JSON)
    line_items: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Sale line items as JSON array",
    )

    # Weather conditions at time of sale (for ML features)
    weather_temp_f: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Temperature in Fahrenheit",
    )

    weather_condition: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Weather condition (e.g., 'sunny', 'rainy')",
    )

    # Market event context
    event_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Associated market/event name",
    )

    # Additional indexes for analytics
    __table_args__ = (
        Index('ix_sales_vendor_date', 'vendor_id', 'sale_date'),
        Index('ix_sales_vendor_square_order', 'vendor_id', 'square_order_id'),
        Index('ix_sales_date_range', 'sale_date'),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Sale(id={self.id}, vendor_id={self.vendor_id}, "
            f"sale_date={self.sale_date}, total_amount={self.total_amount})>"
        )
