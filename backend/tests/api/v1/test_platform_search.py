"""Tests for Amazon Music, Apple Music, SoundCloud, and Tidal search endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.apple_music_service import AppleMusicService

# ─── Amazon Music ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_amazon_service():
    with patch("app.api.v1.amazon_music.amazon_music_service") as mock:
        mock.can_handle = lambda q: "music.amazon.com" in q
        mock.get_playlist_info = AsyncMock(return_value=None)
        mock.get_tracks = AsyncMock(return_value=[])
        yield mock


@pytest.mark.asyncio
async def test_amazon_search_non_url_returns_empty(client, admin_token_headers, mock_amazon_service):
    response = await client.get("/api/v1/amazon_music/search", params={"q": "some song"}, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_amazon_search_url_returns_tracks(client, admin_token_headers, mock_amazon_service):
    mock_amazon_service.get_tracks.return_value = [{"title": "Track A"}]
    response = await client.get(
        "/api/v1/amazon_music/search",
        params={"q": "https://music.amazon.com/tracks/1"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json() == [{"title": "Track A"}]


@pytest.mark.asyncio
async def test_amazon_search_playlist_url(client, admin_token_headers, mock_amazon_service):
    mock_amazon_service.get_playlist_info.return_value = {"title": "My Playlist", "tracks": []}
    response = await client.get(
        "/api/v1/amazon_music/search",
        params={"q": "https://music.amazon.com/playlists/ABC"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["title"] == "My Playlist"


@pytest.mark.asyncio
async def test_amazon_search_playlist_none(client, admin_token_headers, mock_amazon_service):
    mock_amazon_service.get_playlist_info.return_value = None
    mock_amazon_service.get_tracks.return_value = []
    response = await client.get(
        "/api/v1/amazon_music/search",
        params={"q": "https://music.amazon.com/playlists/ABC"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200


# ─── Apple Music ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_apple_service():
    with patch("app.api.v1.apple_music.apple_music_service") as mock:
        mock.can_handle = AppleMusicService().can_handle
        mock.get_playlist_info = AsyncMock(return_value=None)
        mock.get_tracks = AsyncMock(return_value=[])
        mock.search = AsyncMock(return_value=[])
        yield mock


@pytest.mark.asyncio
async def test_apple_search_non_url_delegates_to_keyword_search(client, admin_token_headers, mock_apple_service):
    mock_apple_service.search.return_value = [{"title": "Blinding Lights", "source": "apple_music"}]
    response = await client.get(
        "/api/v1/apple_music/search", params={"q": "blinding lights"}, headers=admin_token_headers
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Blinding Lights"
    mock_apple_service.search.assert_awaited_once()
    mock_apple_service.get_tracks.assert_not_awaited()


@pytest.mark.asyncio
async def test_apple_search_url_returns_tracks(client, admin_token_headers, mock_apple_service):
    mock_apple_service.get_tracks.return_value = [{"title": "Apple Track"}]
    response = await client.get(
        "/api/v1/apple_music/search",
        params={"q": "https://music.apple.com/us/song/123"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Apple Track"


@pytest.mark.asyncio
async def test_apple_search_playlist_url(client, admin_token_headers, mock_apple_service):
    mock_apple_service.get_playlist_info.return_value = {"title": "Apple Playlist"}
    response = await client.get(
        "/api/v1/apple_music/search",
        params={"q": "https://music.apple.com/us/playlist/xyz"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Apple Playlist"


@pytest.mark.asyncio
async def test_apple_search_album_url_no_info(client, admin_token_headers, mock_apple_service):
    mock_apple_service.get_playlist_info.return_value = None
    mock_apple_service.get_tracks.return_value = [{"title": "Album Track"}]
    response = await client.get(
        "/api/v1/apple_music/search",
        params={"q": "https://music.apple.com/us/album/abc"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200


# ─── SoundCloud ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_soundcloud_service():
    with patch("app.api.v1.soundcloud.soundcloud_service") as mock:
        mock.can_handle = lambda q: "soundcloud.com" in q
        mock.get_playlist_info = AsyncMock(return_value=None)
        mock.get_tracks = AsyncMock(return_value=[])
        mock.search = AsyncMock(return_value=[])
        yield mock


@pytest.mark.asyncio
async def test_soundcloud_search_non_url_delegates_to_keyword_search(
    client, admin_token_headers, mock_soundcloud_service
):
    mock_soundcloud_service.search.return_value = [{"title": "SC Result", "source": "soundcloud"}]
    response = await client.get("/api/v1/soundcloud/search", params={"q": "search query"}, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()[0]["title"] == "SC Result"
    mock_soundcloud_service.search.assert_awaited_once()
    mock_soundcloud_service.get_tracks.assert_not_awaited()


@pytest.mark.asyncio
async def test_soundcloud_search_track_url(client, admin_token_headers, mock_soundcloud_service):
    mock_soundcloud_service.get_tracks.return_value = [{"title": "SC Track"}]
    response = await client.get(
        "/api/v1/soundcloud/search",
        params={"q": "https://soundcloud.com/artist/track"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "SC Track"


@pytest.mark.asyncio
async def test_soundcloud_search_sets_url(client, admin_token_headers, mock_soundcloud_service):
    mock_soundcloud_service.get_playlist_info.return_value = {"title": "SC Set"}
    response = await client.get(
        "/api/v1/soundcloud/search",
        params={"q": "https://soundcloud.com/artist/sets/my-set"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "SC Set"


@pytest.mark.asyncio
async def test_soundcloud_search_sets_no_info(client, admin_token_headers, mock_soundcloud_service):
    mock_soundcloud_service.get_playlist_info.return_value = None
    mock_soundcloud_service.get_tracks.return_value = []
    response = await client.get(
        "/api/v1/soundcloud/search",
        params={"q": "https://soundcloud.com/artist/sets/empty"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200


# ─── Tidal ────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_tidal_service():
    with patch("app.api.v1.tidal.tidal_service") as mock:
        mock.get_playlist_info = AsyncMock(return_value=None)
        mock.get_tracks = AsyncMock(return_value=[])
        yield mock


@pytest.mark.asyncio
async def test_tidal_search_non_url(client, admin_token_headers, mock_tidal_service):
    response = await client.get("/api/v1/tidal/search", params={"q": "random"}, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_tidal_search_track_url(client, admin_token_headers, mock_tidal_service):
    mock_tidal_service.get_tracks.return_value = [{"title": "Tidal Track"}]
    response = await client.get(
        "/api/v1/tidal/search",
        params={"q": "https://tidal.com/track/123"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Tidal Track"


@pytest.mark.asyncio
async def test_tidal_search_playlist_url(client, admin_token_headers, mock_tidal_service):
    mock_tidal_service.get_playlist_info.return_value = {"title": "Tidal PL"}
    response = await client.get(
        "/api/v1/tidal/search",
        params={"q": "https://tidal.com/playlist/abc"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Tidal PL"


@pytest.mark.asyncio
async def test_tidal_search_album_url_no_info(client, admin_token_headers, mock_tidal_service):
    mock_tidal_service.get_playlist_info.return_value = None
    mock_tidal_service.get_tracks.return_value = []
    response = await client.get(
        "/api/v1/tidal/search",
        params={"q": "https://tidal.com/album/99"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
