"""Product model for inventory management.

Products can be:
1. Synced from Square catalog
2. Manually created by vendor
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Numeric, Boolean, Text, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantModel


class Product(TenantModel):
    """
    Product represents an item in vendor's inventory.

    Can be synced from Square or manually created.
    """

    __tablename__ = "products"

    # Product Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Product description",
    )

    # Pricing
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Price per unit in USD",
    )

    # Square Integration
    square_item_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square catalog item ID",
    )

    square_variation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square item variation ID",
    )

    square_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last sync from Square",
    )

    # Categorization
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Product category (e.g., 'Vegetables', 'Fruits')",
    )

    tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated tags for search",
    )

    # Inventory
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether product is currently available",
    )

    # Season tracking
    is_seasonal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether product is seasonal",
    )

    season_start_month: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Season start month (1-12)",
    )

    season_end_month: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Season end month (1-12)",
    )

    # Additional indexes for queries
    __table_args__ = (
        Index('ix_products_vendor_category', 'vendor_id', 'category'),
        Index('ix_products_vendor_active', 'vendor_id', 'is_active'),
        Index('ix_products_square_item', 'vendor_id', 'square_item_id'),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Product(id={self.id}, vendor_id={self.vendor_id}, "
            f"name={self.name}, price={self.price})>"
        )
