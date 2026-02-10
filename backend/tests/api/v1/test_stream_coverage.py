import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.track import Track


# Mock cache_manager globally
@pytest.fixture(autouse=True)
def mock_cache():
    with patch("app.api.v1.stream.cache_manager", new_callable=AsyncMock) as m:
        m.get.return_value = None
        yield m


# --- Comprehensive Router Flow Test ---


@pytest.mark.asyncio
async def test_get_track_cover_flow(client, admin_token_headers):
    track_id = str(uuid.uuid4())
    track = Track(id=track_id, title="Mocked Track")

    # Mocking _resolve_track_path
    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = (track, "C:/mock.mp3")

        # Ensure we don't hit FLAC strategy by accident
        mock_audio = MagicMock()
        mock_audio.pictures = None  # CRITICAL: avoid MagicMock-as-truthy

        from mutagen.id3 import APIC, ID3

        # We need to be careful NOT to let mutagen/httpx see MagicMocks in headers
        mock_audio.tags = MagicMock(spec=ID3)
        mock_tag = MagicMock(spec=APIC)
        # MUST BE STRING/BYTES
        mock_tag.data = b"id3data"
        mock_tag.mime = "image/jpeg"
        mock_audio.tags.values.return_value = [mock_tag]

        # Patch ONLY stream's os.path.exists and avoid side_effect limit issues
        with (
            patch("app.api.v1.stream.os.path.exists", return_value=False),
            patch("app.api.v1.stream.MutagenFile", return_value=mock_audio),
            patch("app.api.v1.stream.isinstance", side_effect=lambda x, y: True if y in [ID3, APIC] else False),
        ):
            response = await client.get(f"/api/v1/stream/{track_id}/cover", headers=admin_token_headers)
            assert response.status_code == 200
            assert response.content == b"id3data"
            assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_get_track_cover_not_found(client, admin_token_headers):
    response = await client.get(f"/api/v1/stream/{uuid.uuid4()}/cover", headers=admin_token_headers)
    assert response.status_code == 404


# --- Router Error Handlers ---


@pytest.mark.asyncio
async def test_stream_router_error_handling(client, admin_token_headers):
    un_id = uuid.uuid4()
    with patch("app.api.v1.stream._resolve_stream_url", side_effect=Exception("BOOM")):
        response = await client.get(f"/api/v1/stream/{un_id}.mp3", headers=admin_token_headers)
        assert response.status_code == 500


# --- Resolution Logics ---


@pytest.mark.asyncio
async def test_resolve_stream_url_logic():
    from app.api.v1.stream import _resolve_stream_url

    assert await _resolve_stream_url("abc12345678") == "https://www.youtube.com/watch?v=abc12345678"

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(
            side_effect=[{"artist": "A", "title": "T"}, "https://youtube.com/watch?v=S"]
        )
        url = await _resolve_stream_url("spotify_id_long")
        assert "S" in url


# --- Strategy Extraction ---


def test_extract_art_strategies():
    import mutagen.mp4
    from app.api.v1.stream import _extract_art_flac, _extract_art_mp4, _extract_art_sync

    # MP4
    m = MagicMock()

    class MockCov(bytes):
        pass

    MockCov.imageformat = mutagen.mp4.MP4Cover.FORMAT_JPEG
    m.tags = {"covr": [MockCov(b"m")]}
    assert _extract_art_mp4(m) == (b"m", "image/jpeg")

    # FLAC
    m = MagicMock()
    p = MagicMock()
    p.data = b"f"
    p.mime = "i/f"
    m.pictures = [p]
    assert _extract_art_flac(m) == (b"f", "i/f")

    # Sync Wrapper
    with patch("app.api.v1.stream.MutagenFile", side_effect=ValueError):
        assert _extract_art_sync("/p") == (None, None)


# --- Sync Helper Failure Cases ---


def test_sync_helpers_failures():
    from app.api.v1.stream import _get_spotify_track_sync, _resolve_stream_url_sync

    with patch("app.api.v1.stream.YouTubeService") as m:
        m.return_value.search.return_value = []
        assert _resolve_stream_url_sync({"artist": "A", "title": "T"}) is None
    with patch("app.api.v1.stream.SpotifyService", side_effect=Exception):
        assert _get_spotify_track_sync("id") is None
