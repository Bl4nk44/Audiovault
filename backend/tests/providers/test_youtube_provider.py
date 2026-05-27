from unittest.mock import patch

import pytest

from app.providers.youtube_provider import YouTubeProvider


@pytest.fixture
def youtube_provider():
    with patch("app.providers.youtube_provider.YouTubeService"):
        return YouTubeProvider()


@pytest.mark.asyncio
async def test_can_handle(youtube_provider):
    assert youtube_provider.can_handle("https://www.youtube.com/watch?v=123") is True
    assert youtube_provider.can_handle("https://youtu.be/123") is True
    assert youtube_provider.can_handle("https://music.youtube.com/watch?v=123") is True
    assert youtube_provider.can_handle("https://spotify.com") is False


@pytest.mark.asyncio
async def test_extract_playlist(youtube_provider):
    # Mock return for get_playlist_details
    youtube_provider.service.get_playlist_details.return_value = {
        "title": "My YT Playlist",
        "description": None,
        "image_url": None,
        "tracks": [
            {
                "id": "v1",
                "title": "Video 1",
                "artist": "Author 1",
                "album": "Album 1",
                "duration_ms": 3000,
                "image_url": "img1",
            }
        ],
    }

    result = await youtube_provider.extract_playlist("https://www.youtube.com/playlist?list=PL123")

    assert result is not None
    assert result.title == "My YT Playlist"
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Video 1"
    assert result.tracks[0].source == "youtube"
    assert result.source_id == "PL123"


@pytest.mark.asyncio
async def test_extract_playlist_no_tracks(youtube_provider):
    youtube_provider.service.get_playlist_details.return_value = None

    result = await youtube_provider.extract_playlist("https://www.youtube.com/playlist?list=PL404")
    assert result is None


@pytest.mark.asyncio
async def test_get_track(youtube_provider):
    # Currently get_track returns None in YouTubeProvider
    result = await youtube_provider.get_track("https://www.youtube.com/watch?v=123")
    assert result is None
