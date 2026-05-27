from unittest.mock import AsyncMock, patch

import pytest

from app.providers.spotify_provider import SpotifyProvider


@pytest.fixture
def mock_service():
    with patch("app.providers.spotify_provider.SpotifyService") as mock:
        service_mock = mock.return_value
        service_mock.get_playlist_details = AsyncMock()
        service_mock.get_track = AsyncMock()
        yield service_mock


@pytest.fixture
def spotify_provider(mock_service):
    # The provider instantiates the service in __init__
    return SpotifyProvider()


@pytest.mark.asyncio
async def test_can_handle(spotify_provider):
    assert spotify_provider.can_handle("https://open.spotify.com/track/123") is True
    assert spotify_provider.can_handle("spotify:track:123") is True
    assert spotify_provider.can_handle("https://google.com") is False


@pytest.mark.asyncio
async def test_extract_playlist_from_url(spotify_provider, mock_service):
    # Setup mock return for get_playlist_details
    mock_service.get_playlist_details.return_value = {
        "id": "p1",
        "title": "Playlist 1",
        "image_url": "img_pl",
        "tracks": [
            {
                "id": "t1",
                "title": "Song 1",
                "artist": "Artist 1",
                "album": "Album 1",
                "duration_ms": 1000,
                "image_url": "img1",
                "isrc": "isrc1",
            }
        ],
    }

    result = await spotify_provider.extract_playlist("https://open.spotify.com/playlist/p1")

    assert result is not None
    assert result.title == "Playlist 1"
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Song 1"
    assert result.source == "spotify"

    # Verify ID extraction
    mock_service.get_playlist_details.assert_called_with("p1")


@pytest.mark.asyncio
async def test_get_track(spotify_provider, mock_service):
    mock_service.get_track.return_value = {
        "id": "t1",
        "title": "Song 1",
        "artist": "Artist 1",
        "album": "Album 1",
        "duration_ms": 1000,
        "image_url": "img1",
        "isrc": "isrc1",
    }

    result = await spotify_provider.get_track("https://open.spotify.com/track/t1")

    assert result is not None
    assert result.title == "Song 1"
    assert result.source_id == "t1"

    mock_service.get_track.assert_called_with("t1")
