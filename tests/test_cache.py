"""Tests for the cache module."""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, mock_open
import pytest

from src.youtubesorter.cache import PlaylistCache, CacheStats


@pytest.fixture
def cache():
    """Create a PlaylistCache instance."""
    cache = PlaylistCache(cache_file="data/cache/test_cache.json")
    yield cache
    # Clean up cache file after test
    if os.path.exists("data/cache/test_cache.json"):
        os.remove("data/cache/test_cache.json")


def test_cache_stats_init():
    """Test CacheStats initialization."""
    stats = CacheStats()
    assert stats.hits == 0
    assert stats.misses == 0
    assert stats.expired == 0


def test_cache_stats_reset():
    """Test CacheStats reset."""
    stats = CacheStats()
    stats.hits = 5
    stats.misses = 3
    stats.expired = 2
    stats.reset()
    assert stats.hits == 0
    assert stats.misses == 0
    assert stats.expired == 0


def test_playlist_cache_init():
    """Test PlaylistCache initialization."""
    cache = PlaylistCache(cache_file="data/cache/test_cache.json")
    assert cache.cache_file == "data/cache/test_cache.json"
    assert cache.cache == {}
    assert isinstance(cache.stats, CacheStats)


def test_playlist_cache_init_default():
    """Test PlaylistCache initialization with default path."""
    with patch("os.makedirs") as mock_makedirs:
        cache = PlaylistCache()
        assert cache.cache_file == "data/cache/playlist_cache.json"
        mock_makedirs.assert_called_once_with("data/cache", exist_ok=True)


def test_playlist_cache_load_existing():
    """Test loading existing cache file."""
    cache_data = {
        "key1": {"value": "test1"},
        "key2": {"value": "test2"},
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            cache = PlaylistCache()
            assert cache.cache == cache_data


def test_playlist_cache_load_error():
    """Test error handling when loading cache."""
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = Exception("Test error")
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            cache = PlaylistCache()
            assert cache.cache == {}


def test_playlist_cache_save():
    """Test saving cache to file."""
    cache = PlaylistCache()
    cache.cache = {"key1": {"value": "test1"}}
    with patch("builtins.open", mock_open()) as mock_file:
        cache._save_cache()
        handle = mock_file()
        # Get the actual data written to the file
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        # Parse it back to compare
        actual_data = json.loads(written_data)
        assert actual_data == {"key1": {"value": "test1"}}


def test_playlist_cache_save_error():
    """Test error handling when saving cache."""
    cache = PlaylistCache()
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = Exception("Test error")
        cache._save_cache()  # Should not raise exception


def test_playlist_cache_cleanup_expired():
    """Test cleaning up expired cache entries."""
    now = datetime.now()
    expired = (now - timedelta(seconds=10)).isoformat()
    future = (now + timedelta(seconds=10)).isoformat()

    cache = PlaylistCache()
    cache.cache = {
        "expired": {"value": "test1", "expiry": expired},
        "valid": {"value": "test2", "expiry": future},
        "no_expiry": {"value": "test3"},
    }

    with patch("builtins.open", mock_open()):
        cache._cleanup_expired()
        assert "expired" not in cache.cache
        assert "valid" in cache.cache
        assert "no_expiry" in cache.cache
        assert cache.stats.expired == 1


def test_playlist_cache_get_hit():
    """Test cache hit."""
    cache = PlaylistCache()
    cache.cache = {"key1": {"value": "test1"}}
    value = cache.get("key1")
    assert value == "test1"
    assert cache.stats.hits == 1
    assert cache.stats.misses == 0


def test_playlist_cache_get_miss():
    """Test cache miss."""
    cache = PlaylistCache()
    value = cache.get("nonexistent")
    assert value is None
    assert cache.stats.hits == 0
    assert cache.stats.misses == 1


def test_playlist_cache_get_expired():
    """Test getting expired cache entry."""
    now = datetime.now()
    expired = (now - timedelta(seconds=10)).isoformat()

    cache = PlaylistCache()
    cache.cache = {"key1": {"value": "test1", "expiry": expired}}

    with patch("builtins.open", mock_open()):
        value = cache.get("key1")
        assert value is None
        assert cache.stats.hits == 0
        assert cache.stats.misses == 1
        assert cache.stats.expired == 1
        assert "key1" not in cache.cache


def test_playlist_cache_set():
    """Test setting cache entry."""
    cache = PlaylistCache()
    with patch("builtins.open", mock_open()):
        cache.set("key1", {"data": "test1"})
        assert cache.cache["key1"]["value"] == {"data": "test1"}
        assert "expiry" not in cache.cache["key1"]


def test_playlist_cache_set_with_ttl():
    """Test setting cache entry with TTL."""
    cache = PlaylistCache()
    with patch("builtins.open", mock_open()):
        with patch("datetime.datetime") as mock_datetime:
            now = datetime.now()
            mock_datetime.now.return_value = now

            cache.set("key1", {"data": "test1"}, ttl=60)
            assert cache.cache["key1"]["value"] == {"data": "test1"}
            expected_expiry = now + timedelta(seconds=60)
            actual_expiry = datetime.fromisoformat(cache.cache["key1"]["expiry"])
            assert (
                abs((actual_expiry - expected_expiry).total_seconds()) < 0.1
            )  # Allow 0.1s difference


def test_playlist_cache_invalidate():
    """Test invalidating cache entry."""
    cache = PlaylistCache()
    cache.cache = {"key1": {"value": "test1"}}
    with patch("builtins.open", mock_open()):
        cache.invalidate("key1")
        assert "key1" not in cache.cache


def test_playlist_cache_invalidate_nonexistent():
    """Test invalidating nonexistent cache entry."""
    cache = PlaylistCache()
    with patch("builtins.open", mock_open()):
        cache.invalidate("nonexistent")  # Should not raise exception


def test_playlist_cache_clear():
    """Test clearing cache."""
    cache = PlaylistCache()
    cache.cache = {
        "key1": {"value": "test1"},
        "key2": {"value": "test2"},
    }
    cache.stats.hits = 5
    cache.stats.misses = 3
    cache.stats.expired = 2

    with patch("builtins.open", mock_open()):
        cache.clear()
        assert cache.cache == {}
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0
        assert cache.stats.expired == 0
