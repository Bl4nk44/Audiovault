from unittest.mock import AsyncMock, patch

import pytest

from app.providers.apple_music_provider import AppleMusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata


@pytest.fixture
def apple_music_provider():
    return AppleMusicProvider()


@pytest.mark.asyncio
async def test_can_handle(apple_music_provider):
    with patch("app.providers.apple_music_provider.apple_music_service") as mock_service:
        mock_service.can_handle.side_effect = lambda url: "music.apple.com" in url

        assert apple_music_provider.can_handle("https://music.apple.com/us/album/test/123") is True
        assert apple_music_provider.can_handle("https://spotify.com/track/123") is False


@pytest.mark.asyncio
async def test_extract_playlist(apple_music_provider):
    with patch("app.providers.apple_music_provider.apple_music_service") as mock_service:
        mock_service.get_tracks = AsyncMock(
            return_value=[
                {
                    "id": "1",
                    "title": "Song 1",
                    "artist": "Artist 1",
                    "album": "Album 1",
                    "duration_ms": 1000,
                    "image_url": "img1",
                    "source_url": "url1",
                },
                {
                    "id": "2",
                    "title": "Song 2",
                    "artist": "Artist 2",
                    "album": "Album 1",
                    "duration_ms": 2000,
                    "image_url": "img2",
                    "source_url": "url2",
                },
            ]
        )

        result = await apple_music_provider.extract_playlist("https://music.apple.com/us/playlist/pl.123")

        assert isinstance(result, PlaylistMetadata)
        assert result.title == "Album 1"  # inferred from first track album in provider logic
        assert len(result.tracks) == 2
        assert result.tracks[0].title == "Song 1"
        assert result.tracks[0].source == "apple_music"


@pytest.mark.asyncio
async def test_extract_playlist_no_tracks(apple_music_provider):
    with patch("app.providers.apple_music_provider.apple_music_service") as mock_service:
        mock_service.get_tracks = AsyncMock(return_value=[])

        result = await apple_music_provider.extract_playlist("https://music.apple.com/us/playlist/empty")
        assert result is None


@pytest.mark.asyncio
async def test_get_track(apple_music_provider):
    with patch("app.providers.apple_music_provider.apple_music_service") as mock_service:
        mock_service.get_tracks = AsyncMock(
            return_value=[
                {
                    "id": "1",
                    "title": "Song 1",
                    "artist": "Artist 1",
                    "album": "Album 1",
                    "duration_ms": 1000,
                    "image_url": "img1",
                    "source_url": "url1",
                }
            ]
        )

        result = await apple_music_provider.get_track("https://music.apple.com/us/album/song/1")

        assert isinstance(result, TrackMetadata)
        assert result.title == "Song 1"
        assert result.source == "apple_music"
