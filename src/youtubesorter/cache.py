"""Cache module for storing playlist information."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class CacheStats:
    """Statistics for cache operations."""

    def __init__(self) -> None:
        """Initialize cache stats."""
        self.hits = 0
        self.misses = 0
        self.expired = 0

    def reset(self) -> None:
        """Reset cache stats."""
        self.hits = 0
        self.misses = 0
        self.expired = 0


class PlaylistCache:
    """Cache for playlist information."""

    def __init__(self, cache_file: str = ".youtubesorter_cache.json") -> None:
        """Initialize playlist cache.

        Args:
            cache_file: Path to cache file
        """
        self.cache_file = cache_file
        self.cache: Dict = {}
        self.stats = CacheStats()

        # Load cache from file if it exists
        if os.path.exists(cache_file):
            self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self.cache = json.load(f)
        except Exception as e:
            logger.error("Error loading cache: %s", str(e))
            self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error("Error saving cache: %s", str(e))

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = datetime.now()
        expired = []
        for key, entry in self.cache.items():
            if "expiry" in entry:
                expiry = datetime.fromisoformat(entry["expiry"])
                if now > expiry:
                    expired.append(key)
                    self.stats.expired += 1

        for key in expired:
            del self.cache[key]

        if expired:
            self._save_cache()
            logger.debug("Removed %d expired entries from cache", len(expired))

    def get(self, key: str) -> Optional[Dict]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            self.stats.misses += 1
            return None

        entry = self.cache[key]
        now = datetime.now()

        # Check expiry if set
        if "expiry" in entry:
            expiry = datetime.fromisoformat(entry["expiry"])
            if now > expiry:
                del self.cache[key]
                self._save_cache()
                self.stats.expired += 1
                self.stats.misses += 1
                return None

        self.stats.hits += 1
        return entry.get("value")

    def set(self, key: str, value: Dict, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        entry = {"value": value}

        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
            entry["expiry"] = expiry.isoformat()

        self.cache[key] = entry
        self._save_cache()

    def invalidate(self, key: str) -> None:
        """Invalidate cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self.cache:
            del self.cache[key]
            self._save_cache()

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache = {}
        self._save_cache()
        self.stats.reset()


# Global cache instance
playlist_cache = PlaylistCache()
