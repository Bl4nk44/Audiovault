from unittest.mock import AsyncMock, patch

import pytest

from app.services.soundcloud_service import SoundCloudService


@pytest.fixture
def service():
    return SoundCloudService()


def test_can_handle_soundcloud_url(service):
    assert service.can_handle("https://soundcloud.com/user/track") is True


def test_can_handle_short_url(service):
    assert service.can_handle("https://on.soundcloud.com/abc123") is True


def test_can_handle_non_soundcloud(service):
    assert service.can_handle("https://spotify.com/track/123") is False


@pytest.mark.asyncio
async def test_get_tracks_playlist(service):
    mock_info = {
        "_type": "playlist",
        "entries": [
            {
                "id": "123",
                "title": "Track One",
                "uploader": "Artist One",
                "duration": 180,
                "thumbnail": "http://img.url",
                "webpage_url": "https://soundcloud.com/artist/track-one",
            },
            {
                "id": "456",
                "title": "Track Two",
                "artist": "Artist Two",
                "duration": 240,
                "thumbnail": None,
                "webpage_url": "https://soundcloud.com/artist/track-two",
            },
        ],
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks("https://soundcloud.com/user/sets/my-set")

    assert len(tracks) == 2
    assert tracks[0]["title"] == "Track One"
    assert tracks[0]["artist"] == "Artist One"
    assert tracks[0]["duration_ms"] == 180_000
    assert tracks[0]["source"] == "soundcloud"
    assert tracks[0]["album"] == "SoundCloud"
    assert tracks[1]["artist"] == "Artist Two"


@pytest.mark.asyncio
async def test_get_tracks_single_track(service):
    mock_info = {
        "id": "789",
        "title": "Solo Track",
        "uploader": "Solo Artist",
        "duration": 120,
        "thumbnail": "http://img.url",
        "webpage_url": "https://soundcloud.com/artist/solo",
        # _type NOT 'playlist' → treated as single track
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks("https://soundcloud.com/artist/solo")

    assert len(tracks) == 1
    assert tracks[0]["id"] == "789"
    assert tracks[0]["title"] == "Solo Track"


@pytest.mark.asyncio
async def test_get_tracks_no_info_returns_empty(service):
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = None

        tracks = await service.get_tracks("https://soundcloud.com/user/track")

    assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_skips_entries_without_title(service):
    mock_info = {
        "_type": "playlist",
        "entries": [
            {"id": "1", "title": None, "uploader": "Artist"},
            {"id": "2", "title": "Good Track", "uploader": "Artist"},
            None,
        ],
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks("https://soundcloud.com/user/sets/test")

    assert len(tracks) == 1
    assert tracks[0]["title"] == "Good Track"


@pytest.mark.asyncio
async def test_get_tracks_resolves_short_link(service):
    mock_info = {
        "_type": "playlist",
        "entries": [
            {
                "id": "1",
                "title": "Track",
                "uploader": "Artist",
                "duration": 100,
                "webpage_url": "https://soundcloud.com/a/t",
            },
        ],
    }
    with (
        patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl,
        patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock) as mock_resolve,
    ):
        mock_resolve.return_value = "https://soundcloud.com/artist/track"
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks("https://on.soundcloud.com/abc")

    mock_resolve.assert_called_once_with("https://on.soundcloud.com/abc")
    assert len(tracks) == 1


@pytest.mark.asyncio
async def test_get_tracks_exception_returns_empty(service):
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = RuntimeError("yt-dlp error")

        tracks = await service.get_tracks("https://soundcloud.com/user/track")

    assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_duration_none_when_missing(service):
    mock_info = {
        "entries": [
            {"id": "1", "title": "No Duration Track", "uploader": "Artist", "webpage_url": "https://sc.com/t"},
        ],
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks("https://soundcloud.com/user/track")

    assert tracks[0]["duration_ms"] is None


@pytest.mark.asyncio
async def test_get_playlist_info_valid_set(service):
    mock_info = {
        "_type": "playlist",
        "title": "My SoundCloud Set",
        "thumbnails": [{"url": "http://thumb.url"}],
        "playlist_count": 10,
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        result = await service.get_playlist_info("https://soundcloud.com/user/sets/my-set")

    assert result is not None
    assert result["title"] == "My SoundCloud Set"
    assert result["image_url"] == "http://thumb.url"
    assert result["track_count"] == 10
    assert result["source"] == "soundcloud"
    assert result["type"] == "playlist"


@pytest.mark.asyncio
async def test_get_playlist_info_no_info_returns_none(service):
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = None

        result = await service.get_playlist_info("https://soundcloud.com/user/sets/my-set")

    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_info_single_track_without_sets_returns_none(service):
    mock_info = {
        "_type": "video",
        "title": "Single Track",
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        result = await service.get_playlist_info("https://soundcloud.com/user/track")

    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_info_track_count_from_entries(service):
    mock_info = {
        "_type": "playlist",
        "title": "Set",
        "thumbnails": None,
        "entries": [{"id": "1"}, {"id": "2"}],
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        result = await service.get_playlist_info("https://soundcloud.com/user/sets/test")

    assert result["track_count"] == 2
    assert result["image_url"] is None


@pytest.mark.asyncio
async def test_get_playlist_info_exception_returns_none(service):
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = RuntimeError("yt-dlp error")

        result = await service.get_playlist_info("https://soundcloud.com/user/sets/test")

    assert result is None


@pytest.mark.asyncio
async def test_get_tracks_uses_url_fallback_for_source_url(service):
    """When entry has no webpage_url/url, falls back to the original URL."""
    original_url = "https://soundcloud.com/user/track"
    mock_info = {
        "entries": [
            {"id": "1", "title": "Track", "uploader": "Artist"},
        ],
    }
    with patch("app.services.soundcloud_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        tracks = await service.get_tracks(original_url)

    assert tracks[0]["source_url"] == original_url
