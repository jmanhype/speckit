"""Rate limiting middleware using Redis.

Provides:
- Per-IP rate limiting
- Per-user rate limiting (authenticated requests)
- Sliding window algorithm
- Redis-backed distributed rate limiting

Features graceful degradation:
- Disables rate limiting if Redis is unavailable (fail-open)
- Logs warnings when running without rate limiting
- Continues operation even when Redis fails mid-request
- "Fail-open" approach for security (allows requests on errors)
"""
import logging
import time
from typing import Callable, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from redis import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings


logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window.

    Limits:
    - Anonymous (by IP): 100 requests per minute
    - Authenticated (by vendor_id): 1000 requests per minute
    """

    # Rate limits (requests per window)
    ANONYMOUS_LIMIT = 100
    AUTHENTICATED_LIMIT = 1000

    # Time window in seconds
    WINDOW_SIZE = 60  # 1 minute

    def __init__(self, app=None):
        """Initialize rate limiter with Redis connection.

        Gracefully handles Redis unavailability by disabling rate limiting.

        Args:
            app: FastAPI application instance
        """
        if app is not None:
            super().__init__(app)

        # Connect to Redis with graceful degradation
        try:
            redis_url = str(settings.redis_url)
            self.redis_client = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test connection
            self.redis_client.ping()
            self.degraded_mode = False
            logger.info("Rate limiter connected to Redis - rate limiting enabled")
        except Exception as e:
            logger.warning(
                f"Redis unavailable for rate limiting: {e} - "
                f"rate limiting disabled (fail-open mode)"
            )
            # Fallback: disable rate limiting if Redis unavailable
            self.redis_client = None
            self.degraded_mode = True

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> JSONResponse:
        """Check rate limit before processing request.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or 429 Too Many Requests
        """
        # Skip rate limiting if Redis unavailable
        if self.redis_client is None:
            logger.warning("Rate limiting disabled (Redis unavailable)")
            return await call_next(request)

        # Get identifier (vendor_id or IP)
        identifier, limit = self._get_identifier_and_limit(request)

        # Check rate limit
        allowed, remaining, reset_time = self._check_rate_limit(
            identifier=identifier,
            limit=limit,
        )

        if not allowed:
            # Rate limit exceeded
            correlation_id = getattr(request.state, "correlation_id", "unknown")

            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={
                    "correlation_id": correlation_id,
                    "identifier": identifier,
                    "limit": limit,
                    "path": request.url.path,
                },
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "message": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": self.WINDOW_SIZE,
                    "retry_after": reset_time,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # Continue processing
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_identifier_and_limit(self, request: Request) -> tuple[str, int]:
        """Get rate limit identifier and limit for request.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (identifier, limit)
        """
        # Check if request is authenticated (vendor_id in state)
        if hasattr(request.state, "vendor_id"):
            vendor_id = request.state.vendor_id
            identifier = f"vendor:{vendor_id}"
            limit = self.AUTHENTICATED_LIMIT
        else:
            # Use client IP for anonymous requests
            client_ip = self._get_client_ip(request)
            identifier = f"ip:{client_ip}"
            limit = self.ANONYMOUS_LIMIT

        return identifier, limit

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in chain
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _check_rate_limit(
        self,
        identifier: str,
        limit: int,
    ) -> tuple[bool, int, int]:
        """Check if request is within rate limit using sliding window.

        Args:
            identifier: Rate limit key (e.g., "vendor:123" or "ip:192.168.1.1")
            limit: Maximum requests per window

        Returns:
            Tuple of (allowed, remaining, reset_time)
            - allowed: Whether request is allowed
            - remaining: Remaining requests in window
            - reset_time: Unix timestamp when window resets
        """
        now = time.time()
        window_start = now - self.WINDOW_SIZE

        # Redis key
        key = f"rate_limit:{identifier}"

        try:
            # Use Redis sorted set with timestamps as scores
            pipe = self.redis_client.pipeline()

            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiration to window size
            pipe.expire(key, self.WINDOW_SIZE)

            results = pipe.execute()

            # Get count (before adding current request)
            count = results[1]

            # Calculate remaining requests
            remaining = max(0, limit - count - 1)

            # Calculate reset time (window end)
            reset_time = int(now + self.WINDOW_SIZE)

            # Check if limit exceeded
            allowed = count < limit

            return allowed, remaining, reset_time

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open: allow request if Redis error
            return True, limit, int(now + self.WINDOW_SIZE)


class RateLimitConfig:
    """Configuration for custom rate limits on specific endpoints.

    Usage:
        @router.get("/expensive-operation", dependencies=[Depends(rate_limit(10, 60))])
        def expensive_operation():
            ...
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        redis_client: Optional[Redis] = None,
    ):
        """Initialize rate limit config.

        Args:
            limit: Maximum requests in window
            window_seconds: Time window in seconds
            redis_client: Redis client (uses default if None)
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis_client = redis_client

    async def __call__(self, request: Request) -> None:
        """Check rate limit for request with graceful degradation.

        Fails open (allows request) if Redis is unavailable.

        Args:
            request: FastAPI request

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        from fastapi import HTTPException

        # Get identifier
        if hasattr(request.state, "vendor_id"):
            identifier = f"vendor:{request.state.vendor_id}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{client_ip}"

        # Check rate limit
        key = f"rate_limit:custom:{identifier}:{request.url.path}"
        now = time.time()
        window_start = now - self.window_seconds

        # Try to get Redis client
        try:
            redis_client = self.redis_client or Redis.from_url(
                str(settings.redis_url),
                decode_responses=True,
                socket_connect_timeout=2,
            )
        except Exception as e:
            logger.warning(
                f"Redis unavailable for custom rate limiting: {e} - "
                f"allowing request (fail-open)"
            )
            return  # Fail open

        try:
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window_seconds)

            results = pipe.execute()
            count = results[1]

            if count >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {self.limit} requests per {self.window_seconds} seconds",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                f"Custom rate limit check failed: {e} - "
                f"allowing request (fail-open)"
            )
            # Fail open (no exception, allow request)


def rate_limit(limit: int, window_seconds: int = 60) -> RateLimitConfig:
    """Create rate limit dependency for route.

    Args:
        limit: Maximum requests in window
        window_seconds: Time window in seconds (default 60)

    Returns:
        Rate limit dependency

    Usage:
        @router.post("/bulk-import", dependencies=[Depends(rate_limit(5, 3600))])
        def bulk_import():
            # Limited to 5 requests per hour
            ...
    """
    return RateLimitConfig(limit, window_seconds)
