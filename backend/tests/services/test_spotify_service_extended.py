"""Extended tests for uncovered branches in SpotifyService."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.spotify_service import SpotifyService


@pytest.fixture
def service():
    return SpotifyService()


# ─── get_anonymous_token ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_token_reused_when_not_expired(service):
    service._token = "cached_token"
    service._token_expires_at = time.time() + 3600

    result = await service.get_anonymous_token()

    assert result == "cached_token"


@pytest.mark.asyncio
async def test_token_fetch_exception_returns_empty(service):
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))

        result = await service.get_anonymous_token()

    assert result == ""


# ─── _request ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_no_token_returns_none(service):
    with patch.object(service, "_ensure_token", new_callable=AsyncMock, return_value=""):
        result = await service._request("get", "tracks/abc")
    assert result is None


@pytest.mark.asyncio
async def test_request_401_retries_with_new_token(service):
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.raise_for_status = MagicMock()

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.raise_for_status = MagicMock()
    mock_200.json.return_value = {"id": "t1"}

    call_count = 0

    async def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_401 if call_count == 1 else mock_200

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        with patch.object(service, "_ensure_token", new_callable=AsyncMock, return_value="new_token"):
            result = await service._request("get", "tracks/abc")

    assert result is not None
    assert call_count == 2


@pytest.mark.asyncio
async def test_request_exception_returns_none(service):
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("API error"))
        with patch.object(service, "_ensure_token", new_callable=AsyncMock, return_value="token"):
            result = await service._request("get", "tracks/abc")

    assert result is None


# ─── _format_track album_obj ─────────────────────────────────────────────────


def test_format_track_with_album_obj(service):
    item = {
        "id": "t1",
        "name": "Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "duration_ms": 180000,
    }
    album_obj = {
        "name": "Album",
        "images": [{"url": "http://img.url"}],
    }
    result = service._format_track(item, album_obj=album_obj)
    assert result["album"] == "Album"
    assert result["image_url"] == "http://img.url"


def test_format_track_album_obj_no_images(service):
    item = {"id": "t1", "name": "T", "artists": [], "duration_ms": 0}
    album_obj = {"name": "Album", "images": []}
    result = service._format_track(item, album_obj=album_obj)
    assert result["album"] == "Album"
    assert result["image_url"] is None


# ─── get_track ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_track_returns_none_when_no_data(service):
    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", new_callable=AsyncMock, return_value=None),
    ):
        result = await service.get_track("missing_id")
    assert result is None


# ─── get_playlist_tracks ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_playlist_tracks_breaks_on_no_data(service):
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "id": "pl1",
                "name": "PL",
                "images": [],
                "tracks": {
                    "total": 100,
                    "items": [{"track": {"id": "t1", "name": "T", "artists": [], "duration_ms": 0}}],
                },
            }
        return None  # second page returns None

    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", side_effect=mock_request),
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        tracks = await service.get_playlist_tracks("pl1")

    assert len(tracks) == 1


# ─── get_playlist_details ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_playlist_details_returns_none_when_no_data(service):
    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", new_callable=AsyncMock, return_value=None),
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        result = await service.get_playlist_details("pl1")
    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_details_pagination(service):
    first_response = {
        "id": "pl1",
        "name": "PL",
        "images": [],
        "tracks": {
            "total": 110,
            "items": [{"track": {"id": "t1", "name": "T1", "artists": [], "duration_ms": 0}}] * 100,
        },
    }
    second_response = {"items": [{"track": {"id": "t2", "name": "T2", "artists": [], "duration_ms": 0}}] * 10}

    call_count = 0

    async def mock_request(method, endpoint, params=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return first_response
        return second_response

    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", side_effect=mock_request),
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        result = await service.get_playlist_details("pl1")

    assert result is not None
    assert len(result["tracks"]) == 110


# ─── get_album_tracks ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_album_tracks_no_album_data(service):
    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", new_callable=AsyncMock, return_value=None),
    ):
        result = await service.get_album_tracks("album1")
    assert result == []


@pytest.mark.asyncio
async def test_get_album_tracks_pagination(service):
    album_data = {
        "name": "Album",
        "images": [],
        "artists": [{"name": "Artist", "id": "a1"}],
        "tracks": {
            "total": 60,
            "items": [{"id": f"t{i}", "name": f"T{i}", "artists": [], "duration_ms": 0} for i in range(50)],
        },
    }
    second_page = {"items": [{"id": f"t{i}", "name": f"T{i}", "artists": [], "duration_ms": 0} for i in range(50, 60)]}

    call_count = 0

    async def mock_request(method, endpoint, params=None):
        nonlocal call_count
        call_count += 1
        if "albums/album1" == endpoint and call_count == 1:
            return album_data
        return second_page

    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", side_effect=mock_request),
    ):
        tracks = await service.get_album_tracks("album1")

    assert len(tracks) == 60


# ─── get_album ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_album_returns_none(service):
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=None):
        result = await service.get_album("album1")
    assert result is None


# ─── get_album_details ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_album_details_no_album_returns_none(service):
    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", new_callable=AsyncMock, return_value=None),
    ):
        result = await service.get_album_details("album1")
    assert result is None


# ─── get_artist_top_tracks ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_top_tracks_no_tracks_key(service):
    with patch.object(service, "_request", new_callable=AsyncMock, return_value={"other": "data"}):
        result = await service.get_artist_top_tracks("a1")
    assert result == []


@pytest.mark.asyncio
async def test_get_artist_top_tracks_returns_empty_on_no_data(service):
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=None):
        result = await service.get_artist_top_tracks("a1")
    assert result == []


# ─── get_artist_albums (filtering) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_albums_filters_compilations(service):
    data = {
        "total": 2,
        "items": [
            {"id": "a1", "name": "Real Album", "album_type": "album", "artists": [{"name": "Artist"}]},
            {"id": "a2", "name": "Compilation", "album_type": "compilation", "artists": [{"name": "Artist"}]},
        ],
    }
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=data):
        result = await service.get_artist_albums("artist1")
    names = [a["name"] for a in result]
    assert "Real Album" in names
    assert "Compilation" not in names


@pytest.mark.asyncio
async def test_get_artist_albums_filters_various_artists(service):
    data = {
        "total": 2,
        "items": [
            {"id": "a1", "name": "Real Album", "album_type": "album", "artists": [{"name": "Artist"}]},
            {"id": "a2", "name": "VA Album", "album_type": "album", "artists": [{"name": "Various Artists"}]},
        ],
    }
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=data):
        result = await service.get_artist_albums("artist1")
    names = [a["name"] for a in result]
    assert "Real Album" in names
    assert "VA Album" not in names


@pytest.mark.asyncio
async def test_get_artist_albums_breaks_on_no_data(service):
    async def mock_request(*args, **kwargs):
        return None

    with patch.object(service, "_request", side_effect=mock_request):
        result = await service.get_artist_albums("artist1")
    assert result == []


# ─── get_artist_details ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_details_no_data_returns_none(service):
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=None):
        result = await service.get_artist_details("a1")
    assert result is None


@pytest.mark.asyncio
async def test_get_artist_details_deduplicates_albums(service):
    artist_data = {"id": "a1", "name": "Artist", "images": []}
    album1 = {
        "id": "alb1",
        "name": "Album",
        "album_type": "album",
        "images": [],
        "artists": [{"name": "Artist"}],
        "release_date": "2020",
        "total_tracks": 10,
        "type": "album",
    }
    album2 = {
        "id": "alb2",
        "name": "Album",
        "album_type": "album",
        "images": [],
        "artists": [{"name": "Artist"}],
        "release_date": "2020",
        "total_tracks": 10,
        "type": "album",
    }

    with (
        patch.object(service, "_request", new_callable=AsyncMock, return_value=artist_data),
        patch.object(service, "get_artist_top_tracks", new_callable=AsyncMock, return_value=[]),
        patch.object(service, "get_artist_albums", new_callable=AsyncMock, return_value=[album1, album2]),
    ):
        result = await service.get_artist_details("a1")

    album_names = [a["title"] for a in result["albums"]]
    assert album_names.count("Album") == 1


# ─── search() URL routing ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_resolves_short_link(service):
    mock_response = MagicMock()
    mock_response.url = "https://open.spotify.com/track/abc123"

    with (
        patch("httpx.AsyncClient") as mock_cls,
        patch.object(service, "get_track", new_callable=AsyncMock, return_value={"id": "abc123", "title": "T"}),
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_response)

        result = await service.search("https://spotify.link/abc")

    assert len(result) == 1


@pytest.mark.asyncio
async def test_search_resolves_short_link_exception_continues(service):
    with (
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(side_effect=RuntimeError("network"))

        result = await service.search("https://spotify.link/abc")

    assert result == []


@pytest.mark.asyncio
async def test_search_url_artist_type(service):
    with patch.object(
        service, "_request", new_callable=AsyncMock, return_value={"id": "a1", "name": "Artist", "images": []}
    ):
        result = await service.search("https://open.spotify.com/artist/a1")
    assert len(result) == 1
    assert result[0]["type"] == "artist"


@pytest.mark.asyncio
async def test_search_url_artist_exception_returns_empty(service):
    with patch.object(service, "_request", new_callable=AsyncMock, side_effect=RuntimeError("err")):
        result = await service.search("https://open.spotify.com/artist/a1")
    assert result == []


@pytest.mark.asyncio
async def test_search_url_playlist_type(service):
    with patch.object(
        service,
        "_request",
        new_callable=AsyncMock,
        return_value={"id": "pl1", "name": "PL", "images": [], "tracks": {"total": 5}},
    ):
        result = await service.search("https://open.spotify.com/playlist/pl1")
    assert len(result) == 1
    assert result[0]["type"] == "playlist"


@pytest.mark.asyncio
async def test_search_url_playlist_exception_returns_empty(service):
    with patch.object(service, "get_playlist_details", new_callable=AsyncMock, side_effect=RuntimeError("err")):
        result = await service.search("https://open.spotify.com/playlist/pl1")
    assert result == []


@pytest.mark.asyncio
async def test_search_url_album_type(service):
    with patch.object(
        service,
        "_request",
        new_callable=AsyncMock,
        return_value={"id": "al1", "name": "AL", "images": [], "total_tracks": 10},
    ):
        result = await service.search("https://open.spotify.com/album/al1")
    assert len(result) == 1
    assert result[0]["type"] == "album"


@pytest.mark.asyncio
async def test_search_url_album_exception_returns_empty(service):
    with patch.object(service, "_request", new_callable=AsyncMock, side_effect=RuntimeError("err")):
        result = await service.search("https://open.spotify.com/album/al1")
    assert result == []


@pytest.mark.asyncio
async def test_search_non_url_returns_empty(service):
    result = await service.search("some random query")
    assert result == []
