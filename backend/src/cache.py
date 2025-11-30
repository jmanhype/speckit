"""Redis cache connection and session management."""
from typing import Generator, Optional

from redis import Redis

from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client (optional - can be None if Redis unavailable)
_redis_client: Optional[Redis] = None


def get_redis_client() -> Optional[Redis]:
    """
    Get or create Redis client connection.

    Returns None if Redis is unavailable (graceful degradation).

    Returns:
        Redis client or None
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = str(settings.redis_url)
        client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # Test connection
        client.ping()
        _redis_client = client
        logger.info("Redis client connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable: {e} - operating in degraded mode")
        return None


def get_redis() -> Generator[Optional[Redis], None, None]:
    """
    FastAPI dependency to get Redis client.

    Returns None if Redis is unavailable (graceful degradation).

    Yields:
        Redis client or None

    Usage:
        @router.get("/items")
        def get_cached_items(redis: Redis = Depends(get_redis)):
            if redis:
                cached = redis.get("items")
                if cached:
                    return json.loads(cached)
            # Fallback to database
            return db.query(Item).all()
    """
    client = get_redis_client()
    try:
        yield client
    finally:
        # Redis connections are managed by connection pool
        # No need to close individual connections
        pass


def close_redis():
    """Close Redis connection (call on app shutdown)."""
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
