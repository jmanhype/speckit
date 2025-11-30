"""Base SQLAlchemy model with tenant isolation support."""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TenantMixin:
    """Mixin for multi-tenant models with Row-Level Security support."""

    @declared_attr
    def vendor_id(cls) -> Mapped[UUID]:
        """Foreign key to vendors table for tenant isolation."""
        return mapped_column(
            PGUUID(as_uuid=True),
            nullable=False,
            index=True,
            comment="Tenant isolation: references vendors.id",
        )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Timestamp when record was last updated",
    )


class BaseModel(Base, TimestampMixin):
    """Base model with UUID primary key and timestamps."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="UUID primary key",
    )

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantModel(BaseModel, TenantMixin):
    """Base model for tenant-scoped data with RLS support."""

    __abstract__ = True

    def __repr__(self) -> str:
        """String representation including tenant."""
        return f"<{self.__class__.__name__}(id={self.id}, vendor_id={self.vendor_id})>"
