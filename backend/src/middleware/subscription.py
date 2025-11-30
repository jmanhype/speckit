"""
Subscription tier enforcement middleware

Enforces usage limits based on subscription tier for:
- Recommendations generated per month
- Products tracked
- Venues/markets tracked

Provides graceful degradation when limits are reached.
"""

from datetime import datetime, timedelta
from typing import Callable, Optional
import logging

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.subscription import Subscription, UsageRecord
from src.models.product import Product
from src.models.venue import Venue
from src.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class SubscriptionEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce subscription tier limits

    Checks usage limits before allowing resource-intensive operations.
    Returns 402 Payment Required when limits are exceeded.
    """

    # Endpoints that require limit checks
    LIMIT_CHECKS = {
        "/api/recommendations": "recommendations",
        "/api/products": "products",
        "/api/venues": "venues",
    }

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Check subscription limits before processing request

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or 402 Payment Required if limit exceeded
        """
        # Only check POST requests (creation operations)
        if request.method != "POST":
            return await call_next(request)

        # Check if this endpoint requires limit checking
        limit_type = self._get_limit_type(request.url.path)
        if not limit_type:
            return await call_next(request)

        # Get vendor_id from request state (set by auth middleware)
        vendor_id = getattr(request.state, "vendor_id", None)
        if not vendor_id:
            # No vendor_id means unauthenticated request - let auth handle it
            return await call_next(request)

        # Check subscription limits
        db = SessionLocal()
        try:
            limit_exceeded, limit_info = self._check_limit(
                db, vendor_id, limit_type
            )

            if limit_exceeded:
                logger.warning(
                    f"Subscription limit exceeded for vendor {vendor_id}: "
                    f"{limit_type} ({limit_info['current']}/{limit_info['limit']})"
                )

                return JSONResponse(
                    status_code=402,  # Payment Required
                    content={
                        "error": "subscription_limit_exceeded",
                        "message": (
                            f"You've reached your {limit_info['tier']} tier limit "
                            f"for {limit_type}: {limit_info['limit']} per month. "
                            f"Upgrade your subscription to continue."
                        ),
                        "limit_type": limit_type,
                        "current_usage": limit_info["current"],
                        "limit": limit_info["limit"],
                        "tier": limit_info["tier"],
                        "upgrade_url": "/settings/subscription/upgrade",
                    },
                )

            # Limit not exceeded - continue to handler
            response = await call_next(request)

            # If resource was successfully created (201), record usage
            if response.status_code == 201:
                self._record_usage(db, vendor_id, limit_type)

            return response

        except Exception as e:
            logger.error(f"Error checking subscription limit: {e}", exc_info=True)
            # Fail open - don't block requests on subscription check errors
            return await call_next(request)
        finally:
            db.close()

    def _get_limit_type(self, path: str) -> Optional[str]:
        """
        Determine which limit type to check based on request path

        Args:
            path: Request URL path

        Returns:
            Limit type ("recommendations", "products", "venues") or None
        """
        for endpoint_prefix, limit_type in self.LIMIT_CHECKS.items():
            if path.startswith(endpoint_prefix):
                return limit_type
        return None

    def _check_limit(
        self, db: Session, vendor_id: str, limit_type: str
    ) -> tuple[bool, dict]:
        """
        Check if vendor has exceeded their subscription limit

        Args:
            db: Database session
            vendor_id: Vendor UUID
            limit_type: "recommendations", "products", or "venues"

        Returns:
            Tuple of (limit_exceeded: bool, limit_info: dict)
        """
        # Get vendor's active subscription
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.vendor_id == vendor_id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .first()
        )

        if not subscription:
            # No subscription - use free tier limits
            subscription = Subscription(
                vendor_id=vendor_id,
                tier="free",
                status="active",
                **Subscription.get_tier_limits("free"),
            )

        # Get current usage for this billing period
        current_usage = self._get_current_usage(
            db, vendor_id, limit_type, subscription
        )

        # Check if limit exceeded
        limit_exceeded = subscription.has_reached_limit(limit_type, current_usage)

        # Get limit value
        limit_map = {
            "recommendations": subscription.recommendations_limit,
            "products": subscription.products_limit,
            "venues": subscription.venues_limit,
        }
        limit_value = limit_map.get(limit_type)

        limit_info = {
            "tier": subscription.tier,
            "current": current_usage,
            "limit": limit_value if limit_value is not None else "unlimited",
            "period_start": subscription.current_period_start,
            "period_end": subscription.current_period_end,
        }

        return limit_exceeded, limit_info

    def _get_current_usage(
        self,
        db: Session,
        vendor_id: str,
        limit_type: str,
        subscription: Subscription,
    ) -> int:
        """
        Get current usage count for the billing period

        Args:
            db: Database session
            vendor_id: Vendor UUID
            limit_type: "recommendations", "products", or "venues"
            subscription: Subscription model

        Returns:
            Current usage count
        """
        # Determine billing period
        if subscription.current_period_start and subscription.current_period_end:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
        else:
            # No billing period set - use current month
            now = datetime.utcnow()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)

        # Count resources created in this period
        if limit_type == "recommendations":
            count = (
                db.query(func.count(Recommendation.id))
                .filter(
                    Recommendation.vendor_id == vendor_id,
                    Recommendation.created_at >= period_start,
                    Recommendation.created_at < period_end,
                )
                .scalar()
            )
        elif limit_type == "products":
            count = (
                db.query(func.count(Product.id))
                .filter(
                    Product.vendor_id == vendor_id,
                )
                .scalar()
            )
        elif limit_type == "venues":
            count = (
                db.query(func.count(Venue.id))
                .filter(
                    Venue.vendor_id == vendor_id,
                )
                .scalar()
            )
        else:
            count = 0

        return count or 0

    def _record_usage(
        self, db: Session, vendor_id: str, limit_type: str
    ) -> None:
        """
        Record usage for billing/analytics

        Args:
            db: Database session
            vendor_id: Vendor UUID
            limit_type: "recommendations", "products", or "venues"
        """
        try:
            # Get subscription
            subscription = (
                db.query(Subscription)
                .filter(
                    Subscription.vendor_id == vendor_id,
                    Subscription.status.in_(["active", "trialing"]),
                )
                .first()
            )

            if not subscription:
                return  # No subscription to record against

            # Create usage record
            usage_record = UsageRecord(
                vendor_id=vendor_id,
                subscription_id=subscription.id,
                usage_type=limit_type,
                quantity=1,
                timestamp=datetime.utcnow(),
                billing_period_start=subscription.current_period_start or datetime.utcnow(),
                billing_period_end=subscription.current_period_end or datetime.utcnow() + timedelta(days=30),
            )

            db.add(usage_record)
            db.commit()

            logger.debug(
                f"Recorded usage for vendor {vendor_id}: {limit_type}"
            )

        except Exception as e:
            logger.error(f"Error recording usage: {e}", exc_info=True)
            db.rollback()


# Helper function to check subscription limits programmatically
def check_subscription_limit(
    db: Session, vendor_id: str, limit_type: str
) -> tuple[bool, dict]:
    """
    Check subscription limit programmatically (without middleware)

    Useful for background tasks or batch operations.

    Args:
        db: Database session
        vendor_id: Vendor UUID
        limit_type: "recommendations", "products", or "venues"

    Returns:
        Tuple of (limit_exceeded: bool, limit_info: dict)

    Example:
        from src.middleware.subscription import check_subscription_limit

        exceeded, info = check_subscription_limit(db, vendor_id, "recommendations")
        if exceeded:
            raise HTTPException(
                status_code=402,
                detail=f"Limit exceeded: {info['current']}/{info['limit']}"
            )
    """
    middleware = SubscriptionEnforcementMiddleware(app=None)
    return middleware._check_limit(db, vendor_id, limit_type)


# Helper function to record usage programmatically
def record_usage(db: Session, vendor_id: str, limit_type: str) -> None:
    """
    Record usage programmatically (without middleware)

    Useful for background tasks or batch operations.

    Args:
        db: Database session
        vendor_id: Vendor UUID
        limit_type: "recommendations", "products", or "venues"

    Example:
        from src.middleware.subscription import record_usage

        # After generating recommendation
        record_usage(db, vendor_id, "recommendations")
    """
    middleware = SubscriptionEnforcementMiddleware(app=None)
    middleware._record_usage(db, vendor_id, limit_type)
