"""Extended tests for uncovered branches in DeezerService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.deezer_service import DeezerService


def _mock_aiohttp_response(status=200, json_data=None):
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data or {})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


def _mock_session(response):
    mock_session = MagicMock()
    mock_session.get.return_value = response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


@pytest.fixture
def service():
    return DeezerService()


# ─── search: URL routing ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_routes_album_url(service):
    album_tracks = [
        {"id": 1, "title": "T", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 100, "rank": 0}
    ]
    with patch.object(service, "get_album_tracks", new_callable=AsyncMock, return_value=album_tracks):
        result = await service.search("https://www.deezer.com/album/12345")
    assert result == album_tracks


@pytest.mark.asyncio
async def test_search_routes_playlist_url(service):
    pl_tracks = [
        {"id": 2, "title": "T2", "artist": {"name": "B"}, "album": {"title": "AL"}, "duration": 200, "rank": 0}
    ]
    with patch.object(service, "get_playlist_tracks", new_callable=AsyncMock, return_value=pl_tracks):
        result = await service.search("https://www.deezer.com/playlist/99")
    assert result == pl_tracks


@pytest.mark.asyncio
async def test_search_resolves_short_link(service):
    resolved_url = "https://www.deezer.com/track/12345"
    track = {"id": 12345, "title": "T", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 100, "rank": 0}

    with (
        patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock, return_value=resolved_url),
        patch.object(service, "get_track", new_callable=AsyncMock, return_value=track),
    ):
        result = await service.search("https://deezer.page.link/abc")

    assert len(result) == 1
    assert result[0] == track


@pytest.mark.asyncio
async def test_search_non_200_returns_empty(service):
    resp = _mock_aiohttp_response(status=503)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.search("normal query")
    assert result == []


# ─── get_track error paths ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_track_non_200_returns_none(service):
    resp = _mock_aiohttp_response(status=404)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_track("99999")
    assert result is None


@pytest.mark.asyncio
async def test_get_track_error_in_response_returns_none(service):
    resp = _mock_aiohttp_response(status=200, json_data={"error": {"type": "DataException", "message": "not found"}})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_track("99999")
    assert result is None


# ─── get_album_tracks error paths ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_album_tracks_non_200_returns_empty(service):
    resp = _mock_aiohttp_response(status=404)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_album_tracks("99")
    assert result == []


@pytest.mark.asyncio
async def test_get_album_tracks_success(service):
    track_data = {"data": [
        {"id": 1, "title": "T", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 100, "rank": 0}
    ]}
    resp = _mock_aiohttp_response(status=200, json_data=track_data)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_album_tracks("123")
    assert len(result) == 1


# ─── get_playlist_tracks error paths ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_playlist_tracks_non_200_returns_empty(service):
    resp = _mock_aiohttp_response(status=500)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_playlist_tracks("99")
    assert result == []


@pytest.mark.asyncio
async def test_get_playlist_tracks_success(service):
    data = {"data": [
        {"id": 2, "title": "T2", "artist": {"name": "B"}, "album": {"title": "AL"}, "duration": 200, "rank": 0}
    ]}
    resp = _mock_aiohttp_response(status=200, json_data=data)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_playlist_tracks("123")
    assert len(result) == 1


# ─── get_playlist_details error paths ────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_playlist_details_non_200_returns_none(service):
    resp = _mock_aiohttp_response(status=404)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_playlist_details("99")
    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_details_error_in_response_returns_none(service):
    resp = _mock_aiohttp_response(status=200, json_data={"error": {"type": "DataException"}})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await service.get_playlist_details("99")
    assert result is None


# ─── get_artist_details error paths ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_artist_details_non_200_returns_none(service):
    resp = _mock_aiohttp_response(status=404)
    mock_session = MagicMock()
    mock_session.get.return_value = resp
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_artist_details("99")
    assert result is None


@pytest.mark.asyncio
async def test_get_artist_details_error_in_artist_response_returns_none(service):
    resp = _mock_aiohttp_response(status=200, json_data={"error": {"type": "DataException"}})
    mock_session = MagicMock()
    mock_session.get.return_value = resp
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_artist_details("99")
    assert result is None


# ─── _format_track fallback image paths ──────────────────────────────────────

def test_format_track_cover_big_fallback(service):
    item = {
        "id": 1,
        "title": "T",
        "artist": {"name": "A"},
        "album": {"title": "AL", "cover_big": "http://big.jpg"},
        "duration": 100,
        "rank": 0,
    }
    result = service._format_track(item)
    assert result["image_url"] == "http://big.jpg"


def test_format_track_cover_fallback(service):
    item = {
        "id": 1,
        "title": "T",
        "artist": {"name": "A"},
        "album": {"title": "AL", "cover": "http://cover.jpg"},
        "duration": 100,
        "rank": 0,
    }
    result = service._format_track(item)
    assert result["image_url"] == "http://cover.jpg"


def test_format_track_artist_as_string(service):
    item = {
        "id": 1,
        "title": "T",
        "artist": "String Artist Name",
        "album": {"title": "AL"},
        "duration": 100,
        "rank": 0,
    }
    result = service._format_track(item)
    assert result["artist"] == "String Artist Name"


def test_format_track_artist_as_empty_string_uses_unknown(service):
    item = {
        "id": 1,
        "title": "T",
        "artist": "",
        "album": {"title": "AL"},
        "duration": 100,
        "rank": 0,
    }
    result = service._format_track(item)
    assert result["artist"] == "Unknown Artist"
