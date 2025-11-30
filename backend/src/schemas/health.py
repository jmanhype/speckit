"""Pydantic schemas for health check endpoints."""
from enum import Enum

from pydantic import BaseModel, Field


class DatabaseStatus(str, Enum):
    """Database health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    database: str = Field(..., description="Database status")
    database_message: str = Field(..., description="Database status details")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "development",
                "database": "healthy",
                "database_message": "Database connected",
            }
        }
