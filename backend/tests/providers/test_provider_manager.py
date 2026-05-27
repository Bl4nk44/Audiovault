"""
Tests for ProviderManager to improve coverage.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.manager import ProviderManager


@pytest.fixture
def manager():
    return ProviderManager()


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.name = "test_provider"
    provider.can_handle = MagicMock(return_value=True)
    provider.extract_playlist = AsyncMock(return_value={"name": "Test Playlist"})
    provider.get_track = AsyncMock(return_value={"title": "Test Track"})
    return provider


# =============================================================================
# Registration
# =============================================================================


def test_register_provider(manager, mock_provider):
    """Test registering a provider."""
    manager.register_provider(mock_provider)
    assert len(manager.providers) == 1
    assert manager.providers[0] == mock_provider


# =============================================================================
# Get Provider
# =============================================================================


def test_get_provider_found(manager, mock_provider):
    """Test finding a provider for URL."""
    manager.register_provider(mock_provider)

    result = manager.get_provider("https://example.com/playlist")

    assert result == mock_provider
    mock_provider.can_handle.assert_called_once()


def test_get_provider_not_found(manager):
    """Test when no provider can handle URL."""
    result = manager.get_provider("https://unknown.com")
    assert result is None


def test_get_provider_by_name_found(manager, mock_provider):
    """Test finding provider by name."""
    manager.register_provider(mock_provider)

    result = manager.get_provider_by_name("test_provider")

    assert result == mock_provider


def test_get_provider_by_name_not_found(manager):
    """Test when provider name not registered."""
    result = manager.get_provider_by_name("nonexistent")
    assert result is None


# =============================================================================
# Extract Playlist
# =============================================================================


@pytest.mark.asyncio
async def test_extract_playlist_success(manager, mock_provider):
    """Test extracting playlist with matching provider."""
    manager.register_provider(mock_provider)

    result = await manager.extract_playlist("https://example.com/playlist")

    assert result == {"name": "Test Playlist"}
    mock_provider.extract_playlist.assert_called_once()


@pytest.mark.asyncio
async def test_extract_playlist_no_provider(manager):
    """Test extracting playlist with no matching provider."""
    result = await manager.extract_playlist("https://unknown.com")
    assert result is None


# =============================================================================
# Get Track
# =============================================================================


@pytest.mark.asyncio
async def test_get_track_success(manager, mock_provider):
    """Test getting track with matching provider."""
    manager.register_provider(mock_provider)

    result = await manager.get_track("https://example.com/track")

    assert result == {"title": "Test Track"}
    mock_provider.get_track.assert_called_once()


@pytest.mark.asyncio
async def test_get_track_no_provider(manager):
    """Test getting track with no matching provider."""
    result = await manager.get_track("https://unknown.com")
    assert result is None
