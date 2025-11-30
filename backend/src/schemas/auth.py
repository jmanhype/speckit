"""Pydantic schemas for authentication endpoints."""
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="Vendor email address")
    password: str = Field(..., min_length=8, description="Vendor password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str = Field(..., description="Valid refresh token")
    email: EmailStr = Field(..., description="Vendor email address")


class VendorResponse(BaseModel):
    """Vendor information in auth responses."""

    id: UUID
    email: str
    business_name: str
    subscription_tier: str
    subscription_status: str

    class Config:
        """Pydantic config."""

        from_attributes = True  # For SQLAlchemy models


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(..., description="JWT access token (15 min expiry)")
    refresh_token: str = Field(..., description="JWT refresh token (7 day expiry)")
    token_type: str = Field(default="bearer", description="Token type")
    vendor: VendorResponse = Field(..., description="Authenticated vendor info")


class RefreshResponse(BaseModel):
    """Refresh token response schema."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
