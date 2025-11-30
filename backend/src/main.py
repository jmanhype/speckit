"""MarketPrep FastAPI application.

Main application with routers, middleware, and configuration.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.config import settings
from src.database import SessionLocal
from src.logging_config import setup_logging
from src.middleware.request_logging import RequestLoggingMiddleware
from src.middleware.error_tracking import ErrorTrackingMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.middleware.metrics_middleware import MetricsMiddleware
from src.middleware.compression import CompressionMiddleware
from src.monitoring.metrics import initialize_metrics
from src.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events.

    Args:
        app: FastAPI application
    """
    # Startup
    setup_logging()
    initialize_metrics()
    logger = __import__("logging").getLogger(__name__)
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            'event': 'app_startup',
            'environment': settings.environment,
        }
    )

    yield

    # Shutdown
    logger.info(
        f"Shutting down {settings.app_name}",
        extra={'event': 'app_shutdown'}
    )


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
**MarketPrep** - AI-powered inventory recommendations for farmers market vendors.

## Features

* 🤖 **ML-Powered Recommendations** - Predict optimal inventory using historical data
* 🌤️ **Weather Integration** - Factor weather forecasts into predictions
* 📅 **Event Tracking** - Account for local events affecting foot traffic
* 📊 **Sales Analytics** - Track performance and improve over time
* 🔄 **Feedback Loop** - Learn from actual outcomes to improve accuracy
* 🏢 **Multi-Venue Support** - Manage different market locations
* 🔐 **Secure & Compliant** - Enterprise-grade security and multi-tenancy

## Authentication

All API endpoints (except `/health` and `/`) require authentication:

1. **Register/Login** - Obtain access and refresh tokens
2. **Include Token** - Add `Authorization: Bearer <token>` header to all requests
3. **Refresh Token** - Use refresh token when access token expires (15 min)

## Rate Limits

* **Anonymous**: 100 requests/minute
* **Authenticated**: 1000 requests/minute
* **Custom limits**: Some endpoints have stricter limits (see endpoint docs)

## Correlation IDs

All responses include `X-Correlation-ID` header for request tracing.
Include this ID when reporting issues.
    """,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    contact={
        "name": "MarketPrep Support",
        "email": "support@marketprep.example.com",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints",
        },
        {
            "name": "square",
            "description": "Square POS integration for syncing products and sales",
        },
        {
            "name": "products",
            "description": "Product catalog management",
        },
        {
            "name": "sales",
            "description": "Sales history and analytics",
        },
        {
            "name": "recommendations",
            "description": "AI-powered inventory recommendations",
        },
        {
            "name": "feedback",
            "description": "Recommendation feedback for model improvement",
        },
        {
            "name": "events",
            "description": "Local event tracking and management",
        },
        {
            "name": "monitoring",
            "description": "Health checks and metrics for monitoring",
        },
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters!)
# 1. Security headers (outermost - applies to all responses)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_strict_csp=False,  # Set True for stricter CSP if needed
)

# 2. Response compression (reduce bandwidth usage)
app.add_middleware(CompressionMiddleware, minimum_size=500, compresslevel=6)

# 3. Metrics collection (track all requests for Prometheus)
app.add_middleware(MetricsMiddleware)

# 4. Request logging (logs all requests/responses)
app.add_middleware(RequestLoggingMiddleware)

# 5. Error tracking (tracks and logs all errors with context)
app.add_middleware(
    ErrorTrackingMiddleware,
    enable_error_details=settings.debug,  # Only show error details in debug mode
)

# 6. Rate limiting
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_prefix)

# Import routers
from src.routers import square, products, sales, recommendations, feedback, events, monitoring
app.include_router(square.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(sales.router, prefix=settings.api_v1_prefix)
app.include_router(recommendations.router, prefix=settings.api_v1_prefix)
app.include_router(feedback.router, prefix=settings.api_v1_prefix)
app.include_router(events.router, prefix=settings.api_v1_prefix)

# Monitoring endpoints (no prefix - at root level for standard /health, /metrics paths)
app.include_router(monitoring.router)


@app.get("/")
def read_root() -> dict:
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
