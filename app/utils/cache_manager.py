"""
Cache Manager for API responses and data.

This module provides a centralized caching mechanism to reduce duplicate API calls
and improve performance by storing responses in memory and/or database.
"""

import time
import json
import asyncio
from typing import Any, Dict, Optional, Callable, Tuple, TypeVar, Generic, List
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variable for generic cache value type
T = TypeVar('T')

class CacheEntry(Generic[T]):
    """A cache entry with value and expiration time."""

    def __init__(self, value: T, ttl_seconds: int):
        self.value = value
        self.expiry = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expiry


class CacheManager:
    """
    Manages caching of API responses and other data to reduce duplicate calls.

    Features:
    - In-memory caching with configurable TTL (time-to-live)
    - Automatic cache invalidation based on TTL
    - Support for different cache namespaces
    - Thread-safe operations with locks
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one cache manager instance exists."""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the cache manager."""
        # Main cache dictionary: {namespace: {key: CacheEntry}}
        self._cache: Dict[str, Dict[str, CacheEntry]] = {}
        # Locks for thread safety, per namespace
        self._locks: Dict[str, asyncio.Lock] = {}
        # Default TTL values per namespace (in seconds)
        self._default_ttls: Dict[str, int] = {
            'coingecko': 300,  # 5 minutes for CoinGecko data
            'coingecko_list': 3600,  # 1 hour for CoinGecko coin list
            'coingecko_market': 600,  # 10 minutes for market data
            'cryptopanic': 900,  # 15 minutes for news/sentiment
            'perplexity': 1800,  # 30 minutes for Twitter sentiment
            'market_context': 900,  # 15 minutes for market context
            'technical_analysis': 1200,  # 20 minutes for technical analysis
            'default': 300  # 5 minutes default
        }
        logger.info("Cache manager initialized with default TTLs")

    def get_lock(self, namespace: str) -> asyncio.Lock:
        """Get or create a lock for a namespace."""
        if namespace not in self._locks:
            self._locks[namespace] = asyncio.Lock()
        return self._locks[namespace]

    def get_default_ttl(self, namespace: str) -> int:
        """Get the default TTL for a namespace."""
        return self._default_ttls.get(namespace, self._default_ttls['default'])

    def set_default_ttl(self, namespace: str, ttl_seconds: int) -> None:
        """Set the default TTL for a namespace."""
        self._default_ttls[namespace] = ttl_seconds
        logger.info(f"Set default TTL for {namespace} to {ttl_seconds} seconds")

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            namespace: The cache namespace
            key: The cache key

        Returns:
            The cached value if found and not expired, None otherwise
        """
        if namespace not in self._cache or key not in self._cache[namespace]:
            return None

        cache_entry = self._cache[namespace][key]
        if cache_entry.is_expired():
            # Clean up expired entry
            async with self.get_lock(namespace):
                if key in self._cache[namespace] and self._cache[namespace][key].is_expired():
                    del self._cache[namespace][key]
                    logger.debug(f"Expired cache entry removed: {namespace}:{key}")
            return None

        logger.debug(f"Cache hit: {namespace}:{key}")
        return cache_entry.value

    async def set(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            namespace: The cache namespace
            key: The cache key
            value: The value to cache
            ttl_seconds: Time-to-live in seconds, or None to use the default for the namespace
        """
        if ttl_seconds is None:
            ttl_seconds = self.get_default_ttl(namespace)

        async with self.get_lock(namespace):
            if namespace not in self._cache:
                self._cache[namespace] = {}

            self._cache[namespace][key] = CacheEntry(value, ttl_seconds)
            logger.debug(f"Cache set: {namespace}:{key} (TTL: {ttl_seconds}s)")

    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            namespace: The cache namespace
            key: The cache key

        Returns:
            True if the key was found and deleted, False otherwise
        """
        if namespace not in self._cache or key not in self._cache[namespace]:
            return False

        async with self.get_lock(namespace):
            if key in self._cache[namespace]:
                del self._cache[namespace][key]
                logger.debug(f"Cache entry deleted: {namespace}:{key}")
                return True

        return False

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all entries in a namespace.

        Args:
            namespace: The cache namespace to clear

        Returns:
            Number of entries cleared
        """
        if namespace not in self._cache:
            return 0

        async with self.get_lock(namespace):
            count = len(self._cache[namespace])
            self._cache[namespace] = {}
            logger.info(f"Cleared {count} entries from cache namespace: {namespace}")
            return count

    async def clear_all(self) -> int:
        """
        Clear all cache entries across all namespaces.

        Returns:
            Total number of entries cleared
        """
        total = 0
        for namespace in list(self._cache.keys()):
            total += await self.clear_namespace(namespace)

        logger.info(f"Cleared all caches, total {total} entries removed")
        return total

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'total_namespaces': len(self._cache),
            'total_entries': sum(len(entries) for entries in self._cache.values()),
            'namespaces': {},
            'default_ttls': self._default_ttls.copy()
        }

        for namespace, entries in self._cache.items():
            active_entries = 0
            expired_entries = 0

            for key, entry in entries.items():
                if entry.is_expired():
                    expired_entries += 1
                else:
                    active_entries += 1

            stats['namespaces'][namespace] = {
                'total_entries': len(entries),
                'active_entries': active_entries,
                'expired_entries': expired_entries
            }

        return stats


# Create a singleton instance
cache_manager = CacheManager()


def cached(namespace: str, key_fn: Callable[..., str], ttl_seconds: Optional[int] = None):
    """
    Decorator factory for caching async function results.

    Args:
        namespace: The cache namespace
        key_fn: Function that generates a cache key from the function arguments
        ttl_seconds: Optional TTL override (uses namespace default if None)

    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate the cache key
            cache_key = key_fn(*args, **kwargs)

            # Try to get from cache first
            cached_result = await cache_manager.get(namespace, cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for {func.__name__}: {namespace}:{cache_key}")
                return cached_result

            # Cache miss, call the original function
            logger.info(f"Cache miss for {func.__name__}: {namespace}:{cache_key}")
            result = await func(*args, **kwargs)

            # Cache the result if it's not None
            if result is not None:
                await cache_manager.set(namespace, cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator
