from unittest.mock import MagicMock

import pytest
from app.providers.soundcloud_provider import SoundCloudProvider
from app.providers.spotify_provider import SpotifyProvider
from app.providers.youtube_provider import YouTubeProvider


@pytest.fixture
def spotify_provider():
    p = SpotifyProvider()
    p.client = MagicMock()
    return p


@pytest.fixture
def youtube_provider():
    p = YouTubeProvider()
    # Mock services initialized inside if any
    return p


def test_spotify_can_handle(spotify_provider):
    assert spotify_provider.can_handle("https://open.spotify.com/track/123") is True
    assert spotify_provider.can_handle("https://google.com") is False


@pytest.mark.asyncio
async def test_spotify_get_track(spotify_provider):
    # Mock service
    spotify_provider.service = MagicMock()
    spotify_provider.service.get_track.return_value = {
        "id": "123",
        "title": "Song",
        "artist": "Artist",
        "image_url": "http://img",
        "artists": [{"name": "Artist"}],
        "album": "Album",
        "duration_ms": 1000,
        "external_ids": {"isrc": "US123"},
    }

    track = await spotify_provider.get_track("123")
    assert track.title == "Song"
    assert track.artist == "Artist"
    # assert track.metadata["year"] == "2020"  # TrackMetadata schema doesn't have year/metadata currently


def test_youtube_can_handle(youtube_provider):
    assert youtube_provider.can_handle("https://youtu.be/123") is True
    assert youtube_provider.can_handle("https://google.com") is False


@pytest.mark.asyncio
async def test_youtube_extract_playlist(youtube_provider):
    # Mock internal service
    youtube_provider.service = MagicMock()
    youtube_provider.service.get_playlist_tracks.return_value = [
        {"title": "Video", "artist": "Uploader", "album": "A", "duration_ms": 100, "image_url": "img", "id": "1"}
    ]
    youtube_provider.service.yt.get_playlist.return_value = {"title": "My Playlist"}

    pl = await youtube_provider.extract_playlist("https://youtube.com/playlist?list=PL123")

    assert pl.title == "My Playlist"
    assert len(pl.tracks) == 1
    assert pl.tracks[0].title == "Video"


@pytest.mark.asyncio
async def test_soundcloud_provider():
    p = SoundCloudProvider()
    assert p.name == "soundcloud"

    # Validation logic test
    assert p.can_handle("https://soundcloud.com/user/track") is True
    assert p.can_handle("https://spotify.com") is False
