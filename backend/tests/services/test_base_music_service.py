from unittest.mock import patch

import pytest
from app.services.base_music_service import BaseMusicService


class ConcreteService(BaseMusicService):
    """Minimal concrete subclass for testing."""

    def __init__(self, source="test_source"):
        super().__init__()
        self.source_name = source

    def can_handle(self, url: str) -> bool:
        return "test.com" in url


@pytest.fixture
def service():
    return ConcreteService()


def test_can_handle_base_raises_not_implemented():
    """BaseMusicService.can_handle raises NotImplementedError when called."""

    class Minimal(BaseMusicService):
        def can_handle(self, url: str) -> bool:
            return super().can_handle(url)

    with pytest.raises(NotImplementedError):
        Minimal().can_handle("https://example.com")


def test_concrete_can_handle(service):
    assert service.can_handle("https://test.com/track") is True
    assert service.can_handle("https://other.com/track") is False


@pytest.mark.asyncio
async def test_extract_info_calls_yt_dlp(service):
    mock_info = {"_type": "playlist", "title": "Test Playlist", "entries": []}
    with patch("app.services.base_music_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = mock_info

        result = await service._extract_info("https://test.com/playlist")

    assert result == mock_info
    mock_ydl.return_value.extract_info.assert_called_once_with("https://test.com/playlist", download=False)


@pytest.mark.asyncio
async def test_extract_info_merges_extra_opts(service):
    with patch("app.services.base_music_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = {}

        await service._extract_info("https://test.com", {"playlist_items": "1"})

    call_opts = mock_ydl.call_args[0][0]
    assert call_opts["playlist_items"] == "1"
    assert call_opts["extract_flat"] is True


@pytest.mark.asyncio
async def test_extract_info_returns_none_on_exception(service):
    with patch("app.services.base_music_service.yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = RuntimeError("yt-dlp failed")

        result = await service._extract_info("https://test.com/track")

    assert result is None


@pytest.mark.asyncio
async def test_get_tracks_playlist_with_entries(service):
    mock_info = {
        "_type": "playlist",
        "title": "Test Playlist",
        "entries": [
            {
                "id": "t1",
                "title": "Track One",
                "artist": "Artist A",
                "album": "Album A",
                "duration": 200,
                "thumbnail": "http://img.url",
                "url": "https://test.com/t1",
            },
            {
                "id": "t2",
                "title": "Track Two",
                "uploader": "Artist B",
                "duration": 180,
                "thumbnail": None,
                "webpage_url": "https://test.com/t2",
            },
        ],
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        tracks = await service.get_tracks("https://test.com/playlist")

    assert len(tracks) == 2
    assert tracks[0]["title"] == "Track One"
    assert tracks[0]["artist"] == "Artist A"
    assert tracks[0]["duration_ms"] == 200_000
    assert tracks[0]["source"] == "test_source"
    assert tracks[1]["artist"] == "Artist B"
    assert tracks[1]["album"] == "Test Playlist"  # fallback to playlist title


@pytest.mark.asyncio
async def test_get_tracks_single_track_info(service):
    mock_info = {
        "id": "s1",
        "title": "Single",
        "artist": "Solo",
        "duration": 100,
        "thumbnail": "http://img.url",
        "url": "https://test.com/s1",
        # no 'entries' → single track
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        tracks = await service.get_tracks("https://test.com/s1")

    assert len(tracks) == 1
    assert tracks[0]["title"] == "Single"


@pytest.mark.asyncio
async def test_get_tracks_no_info_returns_empty(service):
    with patch.object(service, "_extract_info", return_value=None):
        tracks = await service.get_tracks("https://test.com/missing")

    assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_skips_entries_without_title(service):
    mock_info = {
        "_type": "playlist",
        "title": "PL",
        "entries": [
            {"id": "1", "title": None},
            None,
            {"id": "2", "title": "Good"},
        ],
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        tracks = await service.get_tracks("https://test.com/pl")

    assert len(tracks) == 1
    assert tracks[0]["title"] == "Good"


@pytest.mark.asyncio
async def test_get_tracks_duration_none_when_absent(service):
    mock_info = {
        "entries": [{"id": "x", "title": "T", "url": "u"}],
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        tracks = await service.get_tracks("https://test.com/t")

    assert tracks[0]["duration_ms"] is None


@pytest.mark.asyncio
async def test_get_playlist_info_valid_playlist(service):
    mock_info = {
        "_type": "playlist",
        "title": "My Playlist",
        "playlist_count": 5,
        "thumbnails": [{"url": "http://small.img"}, {"url": "http://large.img"}],
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        result = await service.get_playlist_info("https://test.com/playlist")

    assert result is not None
    assert result["title"] == "My Playlist"
    assert result["track_count"] == 5
    assert result["image_url"] == "http://large.img"
    assert result["source"] == "test_source"
    assert result["type"] == "playlist"


@pytest.mark.asyncio
async def test_get_playlist_info_not_playlist_type_returns_none(service):
    mock_info = {"_type": "video", "title": "Single"}
    with patch.object(service, "_extract_info", return_value=mock_info):
        result = await service.get_playlist_info("https://test.com/track")

    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_info_none_info_returns_none(service):
    with patch.object(service, "_extract_info", return_value=None):
        result = await service.get_playlist_info("https://test.com/missing")

    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_info_track_count_from_entries(service):
    mock_info = {
        "_type": "playlist",
        "title": "PL",
        "entries": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
    }
    with patch.object(service, "_extract_info", return_value=mock_info):
        result = await service.get_playlist_info("https://test.com/pl")

    assert result["track_count"] == 3
    assert result["image_url"] is None


@pytest.mark.asyncio
async def test_get_playlist_info_calls_extract_with_playlist_items_opt(service):
    with patch.object(service, "_extract_info", return_value=None) as mock_extract:
        await service.get_playlist_info("https://test.com/pl")

    mock_extract.assert_called_once_with("https://test.com/pl", {"playlist_items": "1"})
