"""
Caching utilities for performance optimization

Provides decorators and utilities for caching expensive operations:
- Redis-backed caching with automatic JSON serialization
- TTL support
- Graceful degradation (works without Redis)
- Cache invalidation helpers
"""

import functools
import json
import hashlib
from typing import Any, Callable, Optional
from datetime import timedelta

from redis import Redis

from src.cache import get_redis_client
from src.logging_config import get_logger

logger = get_logger(__name__)


def cache_key(*args, prefix: str = "cache", **kwargs) -> str:
    """
    Generate a cache key from function arguments

    Args:
        *args: Positional arguments
        prefix: Key prefix (default: "cache")
        **kwargs: Keyword arguments

    Returns:
        Cache key in format: prefix:hash

    Examples:
        cache_key(123, "abc", prefix="user") -> "user:a1b2c3..."
        cache_key(user_id=123, product_id=456) -> "cache:d4e5f6..."
    """
    # Create a stable string representation of args
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items()),
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)

    # Hash for shorter keys
    key_hash = hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()[:16]

    return f"{prefix}:{key_hash}"


def redis_cache(
    ttl: Optional[int] = 300,
    key_prefix: str = "cache",
    use_json: bool = True,
):
    """
    Decorator to cache function results in Redis

    Args:
        ttl: Time to live in seconds (default: 300 = 5 minutes, None = never expire)
        key_prefix: Prefix for cache keys
        use_json: Whether to JSON serialize/deserialize values (default: True)

    Usage:
        @redis_cache(ttl=600, key_prefix="weather")
        def get_forecast(lat: float, lon: float):
            # Expensive API call
            return fetch_weather_data(lat, lon)

        # First call: fetches from API, caches result
        forecast = get_forecast(37.7749, -122.4194)

        # Second call (within 10 min): returns cached result
        forecast = get_forecast(37.7749, -122.4194)

    Graceful degradation:
        If Redis is unavailable, the decorator simply calls the function
        without caching (no errors raised).
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            redis = get_redis_client()

            # If Redis unavailable, just call function
            if not redis:
                logger.debug(f"Redis unavailable, skipping cache for {func.__name__}")
                return func(*args, **kwargs)

            # Generate cache key
            key = cache_key(*args, prefix=f"{key_prefix}:{func.__name__}", **kwargs)

            try:
                # Try to get from cache
                cached = redis.get(key)
                if cached:
                    logger.debug(f"Cache hit for {func.__name__}: {key}")
                    if use_json:
                        return json.loads(cached)
                    return cached

                # Cache miss - call function
                logger.debug(f"Cache miss for {func.__name__}: {key}")
                result = func(*args, **kwargs)

                # Store in cache
                if use_json:
                    redis.setex(key, ttl or 0, json.dumps(result, default=str))
                else:
                    if ttl:
                        redis.setex(key, ttl, result)
                    else:
                        redis.set(key, result)

                return result

            except Exception as e:
                logger.warning(f"Cache error for {func.__name__}: {e}")
                # Fallback to calling function
                return func(*args, **kwargs)

        return wrapper

    return decorator


class CacheManager:
    """
    Helper class for cache management operations

    Provides utilities for:
    - Cache invalidation
    - Bulk cache deletion
    - Cache statistics
    """

    def __init__(self, redis: Optional[Redis] = None):
        """
        Initialize cache manager

        Args:
            redis: Redis client (if None, will get from get_redis_client())
        """
        self.redis = redis or get_redis_client()

    def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache keys matching pattern

        Args:
            pattern: Redis key pattern (supports wildcards)
                    Examples: "weather:*", "user:123:*"

        Returns:
            Number of keys deleted

        Example:
            cache_mgr = CacheManager()
            # Invalidate all weather caches
            cache_mgr.invalidate("weather:*")
            # Invalidate specific user's caches
            cache_mgr.invalidate("user:123:*")
        """
        if not self.redis:
            logger.warning("Redis unavailable, cannot invalidate cache")
            return 0

        try:
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache pattern '{pattern}': {e}")
            return 0

    def invalidate_exact(self, key: str) -> bool:
        """
        Invalidate exact cache key

        Args:
            key: Exact cache key

        Returns:
            True if key was deleted, False otherwise
        """
        if not self.redis:
            return False

        try:
            deleted = self.redis.delete(key)
            return bool(deleted)
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {e}")
            return False

    def get_stats(self, prefix: str = "") -> dict:
        """
        Get cache statistics

        Args:
            prefix: Optional key prefix to filter stats

        Returns:
            Dictionary with cache statistics:
            {
                "total_keys": 1523,
                "memory_used_mb": 15.2,
                "hit_rate": 0.85  # If available
            }
        """
        if not self.redis:
            return {"error": "Redis unavailable"}

        try:
            info = self.redis.info("stats")
            memory_info = self.redis.info("memory")

            stats = {
                "total_keys": self.redis.dbsize(),
                "memory_used_mb": round(
                    memory_info.get("used_memory", 0) / (1024 * 1024), 2
                ),
            }

            # Calculate hit rate if stats available
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            if hits + misses > 0:
                stats["hit_rate"] = round(hits / (hits + misses), 3)

            if prefix:
                # Count keys matching prefix
                keys = list(self.redis.scan_iter(match=f"{prefix}*", count=1000))
                stats[f"keys_with_prefix_{prefix}"] = len(keys)

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}

    def clear_all(self, confirm: bool = False) -> bool:
        """
        Clear entire Redis cache

        Args:
            confirm: Must be True to actually clear (safety check)

        Returns:
            True if cleared, False otherwise

        Warning:
            This clears ALL keys in the current Redis database!
            Use with caution, especially in production.
        """
        if not confirm:
            logger.warning("clear_all called without confirmation - no action taken")
            return False

        if not self.redis:
            logger.warning("Redis unavailable, cannot clear cache")
            return False

        try:
            self.redis.flushdb()
            logger.warning("Cleared entire Redis cache (flushdb)")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Convenience functions

def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache keys matching pattern

    Convenience function for CacheManager.invalidate()
    """
    return get_cache_manager().invalidate(pattern)


def cache_stats(prefix: str = "") -> dict:
    """
    Get cache statistics

    Convenience function for CacheManager.get_stats()
    """
    return get_cache_manager().get_stats(prefix)
