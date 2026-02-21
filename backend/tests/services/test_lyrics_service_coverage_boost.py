"""
Coverage boost for LyricsService.
Targets: Genius client init, LRCLIB integration, DB metadata fetching, and cache errors.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.lyrics_service import LyricsService


@pytest.fixture
def service():
    return LyricsService()


@pytest.mark.asyncio
async def test_lyrics_genius_client_init_no_token(service):
    with patch("app.services.lyrics_service.settings") as mock_settings:
        mock_settings.GENIUS_API_TOKEN = None
        client = service._get_genius_client()
        assert client is None


@pytest.mark.asyncio
async def test_lyrics_get_from_lrclib_success(service):
    mock_data = {
        "plainLyrics": "Plain lyrics text",
        "syncedLyrics": "[00:10.00] Synced lyrics",
        "trackName": "Song",
        "artistName": "Artist",
        "albumName": "Album",
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp

        res = await service._get_from_lrclib("Artist", "Song")
        assert res["found"] is True
        assert res["lyrics"] == "Plain lyrics text"
        assert res["synced_lyrics"] == "[00:10.00] Synced lyrics"
        assert res["source"] == "lrclib"


@pytest.mark.asyncio
async def test_lyrics_get_from_lrclib_not_found(service):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        res = await service._get_from_lrclib("Artist", "Unknown")
        assert res["found"] is False


@pytest.mark.asyncio
async def test_lyrics_get_from_db_metadata(service):
    track_id = "00000000-0000-0000-0000-000000000001"
    mock_track = MagicMock()
    mock_track.metadata_content = {"lyrics": "[00:01.00] Line 1"}

    # Mock DB session
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_track
    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_res
    db_mock.__aenter__.return_value = db_mock

    with patch("app.services.lyrics_service.cache_manager", new_callable=AsyncMock) as mock_cache:
        mock_cache.get.return_value = None  # Cache miss
        # Patching where it's imported from since it's a local import inside the function
        with patch("app.db.database.AsyncSessionLocal", return_value=db_mock):
            res = await service.get_lyrics("Artist", "Song", track_id=track_id)
            assert res["found"] is True
            assert res["source"] == "local"
            assert res["synced_lyrics"] == "[00:01.00] Line 1"


@pytest.mark.asyncio
async def test_lyrics_cache_read_error(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.get = AsyncMock(side_effect=Exception("Redis Boom"))
        res = await service._get_from_cache("key", "Artist", "Song")
        assert res is None


@pytest.mark.asyncio
async def test_lyrics_clear_cache_no_redis(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.redis = None
        res = await service.clear_cache("Artist", "Song")
        assert res is False


@pytest.mark.asyncio
async def test_lyrics_fetch_genius_no_song(service):
    mock_genius = MagicMock()
    mock_genius.search_song.return_value = None

    with patch.object(service, "_cache_result", new_callable=AsyncMock) as mock_cache:
        res = await service._fetch_and_cache_genius(mock_genius, "Artist", "Unknown", "key")
        assert res["found"] is False
        assert mock_cache.called
