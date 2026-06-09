"""Unit tests for the module-level helpers in app.api.v1.stream.

Covers the YouTube-URL resolution chain and the streaming error path without
spinning up the full ASGI app — the helpers are plain async functions whose
collaborators (DB, YouTube search, Deezer, cache) are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import stream as stream_mod


def _db_returning(*scalars):
    """AsyncSession mock whose successive execute() calls yield the given scalars."""
    db = MagicMock()
    results = []
    for s in scalars:
        res = MagicMock()
        res.scalar_one_or_none.return_value = s
        results.append(res)
    db.execute = AsyncMock(side_effect=results)
    return db


# ---------------------------------------------------------------------------
# _lookup_track_by_external_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_track_found_on_first_column():
    track = MagicMock()
    db = _db_returning(track)
    result = await stream_mod._lookup_track_by_external_id(db, "spotify123")
    assert result is track


@pytest.mark.asyncio
async def test_lookup_track_not_found_returns_none():
    # Three columns probed, all miss → None
    db = _db_returning(None, None, None)
    result = await stream_mod._lookup_track_by_external_id(db, "nope")
    assert result is None


# ---------------------------------------------------------------------------
# _youtube_url_from_track
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_youtube_url_from_track_direct_id():
    track = MagicMock(youtube_id="abcDEF12345", title="T", artist="A")
    result = await stream_mod._youtube_url_from_track(track)
    assert result == "https://www.youtube.com/watch?v=abcDEF12345"


@pytest.mark.asyncio
async def test_youtube_url_from_track_via_search():
    track = MagicMock(youtube_id=None, title="Song", artist="Band")
    with patch.object(stream_mod, "_youtube_search_url", new_callable=AsyncMock, return_value="https://yt/x") as mock_s:
        result = await stream_mod._youtube_url_from_track(track)
    mock_s.assert_awaited_once_with("Band - Song")
    assert result == "https://yt/x"


@pytest.mark.asyncio
async def test_youtube_url_from_track_no_metadata_returns_none():
    track = MagicMock(youtube_id=None, title=None, artist=None)
    result = await stream_mod._youtube_url_from_track(track)
    assert result is None


# ---------------------------------------------------------------------------
# _youtube_url_from_deezer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_youtube_url_from_deezer_non_numeric_returns_none():
    result = await stream_mod._youtube_url_from_deezer("not-a-number")
    assert result is None


@pytest.mark.asyncio
async def test_youtube_url_from_deezer_track_missing_returns_none():
    with patch.object(stream_mod, "DeezerService") as mock_ds:
        mock_ds.return_value.get_track = AsyncMock(return_value=None)
        result = await stream_mod._youtube_url_from_deezer("12345")
    assert result is None


@pytest.mark.asyncio
async def test_youtube_url_from_deezer_resolves_via_search():
    with (
        patch.object(stream_mod, "DeezerService") as mock_ds,
        patch.object(stream_mod, "_youtube_search_url", new_callable=AsyncMock, return_value="https://yt/d") as mock_s,
    ):
        mock_ds.return_value.get_track = AsyncMock(return_value={"artist": "Dz", "title": "Tr"})
        result = await stream_mod._youtube_url_from_deezer("12345")
    mock_s.assert_awaited_once_with("Dz - Tr")
    assert result == "https://yt/d"


# ---------------------------------------------------------------------------
# _resolve_stream_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_stream_url_cache_hit():
    with patch.object(stream_mod, "cache_manager") as cache:
        cache.get = AsyncMock(return_value="https://cached")
        result = await stream_mod._resolve_stream_url("anyid", MagicMock())
    assert result == "https://cached"


@pytest.mark.asyncio
async def test_resolve_stream_url_direct_11_char_id():
    with patch.object(stream_mod, "cache_manager") as cache:
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        result = await stream_mod._resolve_stream_url("dQw4w9WgXcQ", MagicMock())
    assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_stream_url_falls_back_to_deezer():
    db = _db_returning(None, None, None)  # external-id lookup misses
    with (
        patch.object(stream_mod, "cache_manager") as cache,
        patch.object(stream_mod, "_youtube_url_from_deezer", new_callable=AsyncMock, return_value="https://yt/dz"),
    ):
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        result = await stream_mod._resolve_stream_url("987654", db)
    assert result == "https://yt/dz"


@pytest.mark.asyncio
async def test_resolve_stream_url_not_found_raises_404():
    db = _db_returning(None, None, None)
    with (
        patch.object(stream_mod, "cache_manager") as cache,
        patch.object(stream_mod, "_youtube_url_from_deezer", new_callable=AsyncMock, return_value=None),
    ):
        cache.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await stream_mod._resolve_stream_url("987654", db)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# stream_track — generic 500 on unexpected error (no exception leak)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_track_generic_500_on_unexpected_error():
    with patch.object(stream_mod, "_resolve_stream_url", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        with pytest.raises(HTTPException) as exc:
            await stream_mod.stream_track("id", MagicMock(), MagicMock())
    assert exc.value.status_code == 500
    # Raw exception text must not leak to the client
    assert exc.value.detail == "Internal streaming error"
    assert "boom" not in exc.value.detail
