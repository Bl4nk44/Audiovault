"""
Tests for CacheManager.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache import CacheManager


@pytest.fixture
def cache_manager():
    return CacheManager()


@pytest.mark.asyncio
async def test_connect(cache_manager):
    with patch("redis.asyncio.from_url") as mock_from_url:
        await cache_manager.connect()
        assert cache_manager.redis is not None
        mock_from_url.assert_called_once()


@pytest.mark.asyncio
async def test_close(cache_manager):
    mock_redis = AsyncMock()
    cache_manager.redis = mock_redis
    await cache_manager.close()
    mock_redis.close.assert_called_once()

    # Test close without redis
    cache_manager.redis = None
    await cache_manager.close()  # Should not raise


@pytest.mark.asyncio
async def test_get_auto_connect(cache_manager):
    mock_redis = AsyncMock()
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        mock_redis.get.return_value = "value"

        # Test get triggers connect if redis is None
        val = await cache_manager.get("key")
        assert val == "value"
        assert cache_manager.redis == mock_redis
        mock_redis.get.assert_called_with("key")


@pytest.mark.asyncio
async def test_set_auto_connect(cache_manager):
    mock_redis = AsyncMock()
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        # Test set triggers connect if redis is None
        await cache_manager.set("key", "value", expire=60)
        assert cache_manager.redis == mock_redis
        mock_redis.set.assert_called_with("key", "value", ex=60)
