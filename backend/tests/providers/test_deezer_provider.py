from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.providers.deezer_provider import DeezerProvider
from app.schemas.metadata import PlaylistMetadata


@pytest_asyncio.fixture
async def deezer_provider():
    return DeezerProvider()


@pytest.mark.asyncio
async def test_can_handle(deezer_provider):
    assert deezer_provider.can_handle("https://www.deezer.com/track/123") is True
    assert deezer_provider.can_handle("https://deezer.com/playlist/456") is True
    assert deezer_provider.can_handle("https://spotify.com/track/123") is False


@pytest.mark.asyncio
async def test_extract_playlist_track(deezer_provider):
    with patch("app.providers.deezer_provider.deezer_service") as mock_service:
        mock_service.get_track = AsyncMock(
            return_value={
                "id": "123",
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "duration_ms": 180000,
                "image_url": "http://img.url",
            }
        )

        result = await deezer_provider.extract_playlist("https://deezer.com/track/123")

        assert isinstance(result, PlaylistMetadata)
        assert result.title == "Deezer Track"
        assert len(result.tracks) == 1
        track = result.tracks[0]
        assert track.title == "Test Song"
        assert track.source_id == "123"
        assert track.source == "deezer"


@pytest.mark.asyncio
async def test_extract_playlist_playlist(deezer_provider):
    with patch("app.providers.deezer_provider.deezer_service") as mock_service:
        mock_service.get_playlist_tracks = AsyncMock(
            return_value=[
                {
                    "id": "1",
                    "title": "Song 1",
                    "artist": "Artist 1",
                    "album": "Album 1",
                },
                {
                    "id": "2",
                    "title": "Song 2",
                    "artist": "Artist 2",
                    "album": "Album 2",
                },
            ]
        )

        result = await deezer_provider.extract_playlist("https://deezer.com/playlist/999")

        assert result.title == "Deezer Playlist"
        assert len(result.tracks) == 2
        assert result.tracks[0].title == "Song 1"


@pytest.mark.asyncio
async def test_extract_playlist_invalid(deezer_provider):
    result = await deezer_provider.extract_playlist("https://google.com")
    assert result is None
