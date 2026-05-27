from unittest.mock import AsyncMock, patch

import pytest

from app.services.apple_music_service import AppleMusicService


@pytest.fixture
def service():
    return AppleMusicService()


def test_can_handle_full_url(service):
    assert service.can_handle("https://music.apple.com/us/album/123") is True


def test_can_handle_short_url(service):
    assert service.can_handle("https://apple.co/3xyz") is True


def test_can_handle_other_url(service):
    assert service.can_handle("https://spotify.com/track/abc") is False


@pytest.mark.asyncio
async def test_resolve_url_non_short_link_unchanged(service):
    url = "https://music.apple.com/us/album/abc"
    result = await service._resolve_url(url)
    assert result == url


@pytest.mark.asyncio
async def test_resolve_url_short_link_resolved(service):
    with patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = "https://music.apple.com/us/album/abc"
        result = await service._resolve_url("https://apple.co/3xyz")
    mock_resolve.assert_called_once_with("https://apple.co/3xyz")
    assert result == "https://music.apple.com/us/album/abc"


@pytest.mark.asyncio
async def test_get_tracks_resolves_short_link_then_delegates(service):
    resolved = "https://music.apple.com/us/playlist/my-list"
    mock_tracks = [{"id": "t1", "title": "Track", "artist": "Artist", "source": "apple_music"}]
    with (
        patch.object(service, "_resolve_url", new_callable=AsyncMock, return_value=resolved),
        patch(
            "app.services.base_music_service.BaseMusicService.get_tracks",
            new_callable=AsyncMock,
            return_value=mock_tracks,
        ),
    ):
        tracks = await service.get_tracks("https://apple.co/3xyz")

    assert tracks == mock_tracks


@pytest.mark.asyncio
async def test_get_tracks_full_url_skips_redirect(service):
    url = "https://music.apple.com/us/album/abc"
    mock_tracks = [{"id": "t1", "title": "T", "artist": "A", "source": "apple_music"}]
    with patch(
        "app.services.base_music_service.BaseMusicService.get_tracks",
        new_callable=AsyncMock,
        return_value=mock_tracks,
    ):
        tracks = await service.get_tracks(url)
    assert tracks == mock_tracks


@pytest.mark.asyncio
async def test_get_playlist_info_resolves_short_link(service):
    resolved = "https://music.apple.com/us/playlist/my-list"
    mock_info = {"id": resolved, "title": "My Playlist", "source": "apple_music"}
    with (
        patch.object(service, "_resolve_url", new_callable=AsyncMock, return_value=resolved),
        patch(
            "app.services.base_music_service.BaseMusicService.get_playlist_info",
            new_callable=AsyncMock,
            return_value=mock_info,
        ),
    ):
        result = await service.get_playlist_info("https://apple.co/3xyz")

    assert result == mock_info


@pytest.mark.asyncio
async def test_get_playlist_info_full_url(service):
    url = "https://music.apple.com/us/playlist/my-list"
    mock_info = {"id": url, "title": "PL", "source": "apple_music"}
    with patch(
        "app.services.base_music_service.BaseMusicService.get_playlist_info",
        new_callable=AsyncMock,
        return_value=mock_info,
    ):
        result = await service.get_playlist_info(url)
    assert result == mock_info
