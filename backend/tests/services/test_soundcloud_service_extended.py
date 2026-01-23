"""
Extended tests for SoundCloudService to increase code coverage.
Covers: can_handle, get_tracks, get_playlist_info.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.soundcloud_service import SoundCloudService


@pytest.fixture
def soundcloud_service():
    """Create SoundCloudService instance."""
    return SoundCloudService()


# =============================================================================
# can_handle
# =============================================================================


def test_can_handle_soundcloud_url(soundcloud_service):
    """Test can_handle with SoundCloud URL."""
    assert soundcloud_service.can_handle("https://soundcloud.com/artist/track") is True


def test_can_handle_short_url(soundcloud_service):
    """Test can_handle with short SoundCloud URL."""
    assert soundcloud_service.can_handle("https://on.soundcloud.com/abc") is True


def test_can_handle_other_url(soundcloud_service):
    """Test can_handle with non-SoundCloud URL."""
    assert soundcloud_service.can_handle("https://youtube.com/watch?v=123") is False


def test_can_handle_spotify_url(soundcloud_service):
    """Test can_handle with Spotify URL."""
    assert soundcloud_service.can_handle("https://open.spotify.com/track/123") is False


# =============================================================================
# get_tracks
# =============================================================================


@pytest.mark.asyncio
async def test_get_tracks_single_track(soundcloud_service):
    """Test extracting single track."""
    mock_info = {
        "_type": "video",
        "id": "12345",
        "title": "Test Track",
        "uploader": "Test Artist",
        "duration": 300,
        "thumbnail": "http://thumb.jpg",
        "webpage_url": "https://soundcloud.com/artist/track",
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/artist/track")

        assert len(tracks) == 1
        assert tracks[0]["title"] == "Test Track"
        assert tracks[0]["artist"] == "Test Artist"
        assert tracks[0]["source"] == "soundcloud"


@pytest.mark.asyncio
async def test_get_tracks_playlist(soundcloud_service):
    """Test extracting playlist tracks."""
    mock_info = {
        "_type": "playlist",
        "entries": [
            {
                "id": "1",
                "title": "Track 1",
                "uploader": "Artist",
                "duration": 200,
                "webpage_url": "https://soundcloud.com/a/t1",
            },
            {
                "id": "2",
                "title": "Track 2",
                "artist": "Artist 2",
                "duration": 250,
                "webpage_url": "https://soundcloud.com/a/t2",
            },
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/artist/sets/myplaylist")

        assert len(tracks) == 2


@pytest.mark.asyncio
async def test_get_tracks_no_info(soundcloud_service):
    """Test get_tracks when no info returned."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = None
        mock_ydl.return_value = mock_instance

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/invalid")

        assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_error(soundcloud_service):
    """Test get_tracks with extraction error."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = Exception("Error")

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/artist/track")

        assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_short_link(soundcloud_service):
    """Test get_tracks with short link resolution."""
    mock_info = {
        "id": "123",
        "title": "Short Track",
        "uploader": "Artist",
        "duration": 180,
        "webpage_url": "https://soundcloud.com/artist/track",
    }

    with patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = "https://soundcloud.com/artist/track"

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = MagicMock()
            mock_instance.extract_info.return_value = mock_info
            mock_ydl.return_value = mock_instance

            _ = await soundcloud_service.get_tracks("https://on.soundcloud.com/abc")

            mock_resolve.assert_called_once()


@pytest.mark.asyncio
async def test_get_tracks_null_entry(soundcloud_service):
    """Test get_tracks with null entries in playlist."""
    mock_info = {
        "_type": "playlist",
        "entries": [
            None,
            {"id": "1", "title": "Valid Track", "uploader": "A", "duration": 100, "webpage_url": "url"},
            None,
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/sets/playlist")

        assert len(tracks) == 1


@pytest.mark.asyncio
async def test_get_tracks_no_title(soundcloud_service):
    """Test get_tracks skips entries without title."""
    mock_info = {
        "_type": "playlist",
        "entries": [
            {"id": "1", "uploader": "A", "duration": 100},  # No title
            {"id": "2", "title": "Has Title", "uploader": "B", "duration": 150, "webpage_url": "url"},
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        tracks = await soundcloud_service.get_tracks("https://soundcloud.com/sets/p")

        assert len(tracks) == 1
        assert tracks[0]["title"] == "Has Title"


# =============================================================================
# get_playlist_info
# =============================================================================


@pytest.mark.asyncio
async def test_get_playlist_info_success(soundcloud_service):
    """Test getting playlist info."""
    mock_info = {
        "_type": "playlist",
        "title": "My Playlist",
        "thumbnails": [{"url": "http://thumb.jpg"}],
        "playlist_count": 15,
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        info = await soundcloud_service.get_playlist_info("https://soundcloud.com/artist/sets/playlist")

        assert info is not None
        assert info["title"] == "My Playlist"
        assert info["source"] == "soundcloud"
        assert info["track_count"] == 15


@pytest.mark.asyncio
async def test_get_playlist_info_no_playlist_count(soundcloud_service):
    """Test playlist info with entries instead of count."""
    mock_info = {"_type": "playlist", "title": "Playlist", "entries": [{}, {}, {}]}

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        info = await soundcloud_service.get_playlist_info("https://soundcloud.com/a/sets/p")

        assert info["track_count"] == 3


@pytest.mark.asyncio
async def test_get_playlist_info_not_playlist(soundcloud_service):
    """Test get_playlist_info with non-playlist URL."""
    mock_info = {"_type": "video", "title": "Single Track"}

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance

        info = await soundcloud_service.get_playlist_info("https://soundcloud.com/artist/track")

        assert info is None


@pytest.mark.asyncio
async def test_get_playlist_info_no_info(soundcloud_service):
    """Test get_playlist_info when no info returned."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = None
        mock_ydl.return_value = mock_instance

        info = await soundcloud_service.get_playlist_info("https://soundcloud.com/invalid")

        assert info is None


@pytest.mark.asyncio
async def test_get_playlist_info_error(soundcloud_service):
    """Test get_playlist_info with error."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = Exception("Error")

        info = await soundcloud_service.get_playlist_info("https://soundcloud.com/sets/p")

        assert info is None
