"""Extended tests for uncovered branches in LyricsService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.lyrics_service import LyricsService


@pytest.fixture
def service():
    return LyricsService()


# ─── get_lyrics early return ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_lyrics_empty_artist_returns_none(service):
    result = await service.get_lyrics("", "Song Title")
    assert result is None


@pytest.mark.asyncio
async def test_get_lyrics_empty_title_returns_none(service):
    result = await service.get_lyrics("Artist", "")
    assert result is None


# ─── _get_genius_client ───────────────────────────────────────────────────────

def test_get_genius_client_no_token_returns_none(service):
    with patch("app.services.lyrics_service.settings") as mock_settings:
        del mock_settings.GENIUS_API_TOKEN  # simulate missing attr via getattr default
        mock_settings.__class__ = type("Settings", (), {})
        result = service._get_genius_client()
    assert result is None


def test_get_genius_client_with_token_initializes(service):
    mock_genius_instance = MagicMock()
    with (
        patch("app.services.lyrics_service.settings") as mock_settings,
        patch("lyricsgenius.Genius", return_value=mock_genius_instance),
    ):
        mock_settings.GENIUS_API_TOKEN = "test_token"
        result = service._get_genius_client()
    assert result is mock_genius_instance


def test_get_genius_client_exception_returns_none(service):
    with (
        patch("app.services.lyrics_service.settings") as mock_settings,
        patch("lyricsgenius.Genius", side_effect=RuntimeError("lyricsgenius broken")),
    ):
        mock_settings.GENIUS_API_TOKEN = "token"
        result = service._get_genius_client()
    assert result is None


def test_get_genius_client_returns_cached_instance(service):
    sentinel = MagicMock()
    service._genius = sentinel
    assert service._get_genius_client() is sentinel


# ─── _get_from_lrclib ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_from_lrclib_200_response(service):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "plainLyrics": "Plain text",
        "syncedLyrics": "[00:01.00]Plain text",
        "trackName": "Song",
        "artistName": "Artist",
        "albumName": "Album",
    }

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await service._get_from_lrclib("Artist", "Song")

    assert result["found"] is True
    assert result["lyrics"] == "Plain text"
    assert result["source"] == "lrclib"


@pytest.mark.asyncio
async def test_get_from_lrclib_exception(service):
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))

        result = await service._get_from_lrclib("Artist", "Song")

    assert result["found"] is False


# ─── _get_from_cache ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_from_cache_exception_returns_none(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.get = AsyncMock(side_effect=RuntimeError("redis error"))
        result = await service._get_from_cache("key", "Artist", "Song")
    assert result is None


# ─── _fetch_and_cache_genius ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_and_cache_genius_exception_returns_none(service):
    mock_genius = MagicMock()
    mock_genius.search_song.side_effect = RuntimeError("genius error")

    result = await service._fetch_and_cache_genius(mock_genius, "Artist", "Song", "key")
    assert result is None


# ─── _cache_result ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_result_exception_doesnt_raise(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.set = AsyncMock(side_effect=RuntimeError("redis down"))
        await service._cache_result("key", {"found": True}, 3600)  # must not raise


# ─── clear_cache ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clear_cache_no_redis_returns_false(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.redis = None
        result = await service.clear_cache("Artist", "Song")
    assert result is False


@pytest.mark.asyncio
async def test_clear_cache_exception_returns_false(service):
    with patch("app.services.lyrics_service.cache_manager") as mock_cache:
        mock_cache.redis = AsyncMock()
        mock_cache.redis.delete = AsyncMock(side_effect=RuntimeError("redis error"))
        result = await service.clear_cache("Artist", "Song")
    assert result is False


# ─── get_lyrics lrclib found → cache then return ─────────────────────────────

@pytest.mark.asyncio
async def test_get_lyrics_lrclib_found_caches_result(service):
    lrclib_result = {
        "found": True, "lyrics": "Line 1", "synced_lyrics": "[00:01]Line 1", "source": "lrclib"
    }
    with (
        patch.object(service, "_get_from_cache", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_get_from_lrclib", new_callable=AsyncMock, return_value=lrclib_result),
        patch.object(service, "_cache_result", new_callable=AsyncMock) as mock_cache,
    ):
        result = await service.get_lyrics("Artist", "Song")

    assert result["found"] is True
    mock_cache.assert_called_once()


# ─── get_lyrics with track_id (DB metadata path) ─────────────────────────────

@pytest.mark.asyncio
async def test_get_lyrics_db_metadata_found_synced(service):
    mock_track = MagicMock()
    mock_track.metadata_content = {"lyrics": "[00:01]Line\n[00:05]End"}

    with (
        patch.object(service, "_get_from_cache", new_callable=AsyncMock, return_value=None),
        patch("app.db.database.AsyncSessionLocal") as mock_session_cls,
        patch.object(service, "_cache_result", new_callable=AsyncMock),
    ):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_track
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await service.get_lyrics("Artist", "Song", track_id="00000000-0000-0000-0000-000000000001")

    assert result["found"] is True
    assert result["source"] == "local"
    assert result["synced_lyrics"] is not None


@pytest.mark.asyncio
async def test_get_lyrics_db_metadata_exception_continues_to_lrclib(service):
    lrclib_data = {"found": False, "lyrics": None, "synced_lyrics": None}

    with (
        patch.object(service, "_get_from_cache", new_callable=AsyncMock, return_value=None),
        patch("app.db.database.AsyncSessionLocal") as mock_session_cls,
        patch.object(service, "_get_from_lrclib", new_callable=AsyncMock, return_value=lrclib_data),
        patch.object(service, "_get_genius_client", return_value=None),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await service.get_lyrics("Artist", "Song", track_id="00000000-0000-0000-0000-000000000001")

    assert result == lrclib_data
