"""
Tests for Browse API routes — TDD Red Phase.

Covers:
- GET /browse/search — multi-source search
- GET /browse/track/{source}/{id} — track details
- GET /browse/artist/{source}/{id} — artist details
- GET /browse/album/{source}/{id} — album details
- GET /browse/playlist/{source}/{id} — playlist details
- Unauthenticated access returns 401
"""

from unittest.mock import AsyncMock, patch

import pytest

# --- Mock Data ---

MOCK_SEARCH_RESULTS = [
    {
        "id": "dz-123",
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "album": "A Night at the Opera",
        "duration_ms": 354000,
        "image_url": "https://deezer.com/img/123.jpg",
        "source": "deezer",
        "isrc": "GBUM71029604",
    }
]

MOCK_ARTIST = {
    "id": "27",
    "name": "Queen",
    "image_url": "https://deezer.com/img/queen.jpg",
    "source": "deezer",
    "type": "artist",
}

MOCK_ALBUM = {
    "id": "456",
    "title": "A Night at the Opera",
    "tracks": [],
    "source": "deezer",
}

MOCK_PLAYLIST = {
    "id": "789",
    "title": "Classic Rock",
    "tracks": [],
    "source": "deezer",
}

MOCK_TRACK = {
    "id": "123",
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "source": "deezer",
}


# --- Search Tests ---


@pytest.mark.asyncio
async def test_browse_search(client, admin_token_headers):
    """GET /browse/search should return multi-source results."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.search_tracks = AsyncMock(return_value=MOCK_SEARCH_RESULTS)
        mock_orch.search_artists = AsyncMock(return_value=[MOCK_ARTIST])

        response = await client.get(
            "/api/v1/browse/search",
            params={"q": "Bohemian Rhapsody"},
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_browse_search_with_type_artist(client, admin_token_headers):
    """GET /browse/search?type=artist should return artist results."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.search_artists = AsyncMock(return_value=[MOCK_ARTIST])

        response = await client.get(
            "/api/v1/browse/search",
            params={"q": "Queen", "type": "artist"},
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_browse_search_unauthenticated(client):
    """Search without auth should return 401."""
    response = await client.get(
        "/api/v1/browse/search",
        params={"q": "test"},
    )
    assert response.status_code == 401


# --- Track Details Tests ---


@pytest.mark.asyncio
async def test_browse_track(client, admin_token_headers):
    """GET /browse/track/{source}/{id} should return track details."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_track_details = AsyncMock(return_value=MOCK_TRACK)

        response = await client.get(
            "/api/v1/browse/track/deezer/123",
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Bohemian Rhapsody"


@pytest.mark.asyncio
async def test_browse_track_not_found(client, admin_token_headers):
    """Non-existent track should return 404."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_track_details = AsyncMock(return_value=None)

        response = await client.get(
            "/api/v1/browse/track/deezer/nonexistent",
            headers=admin_token_headers,
        )

    assert response.status_code == 404


# --- Artist Details Tests ---


@pytest.mark.asyncio
async def test_browse_artist(client, admin_token_headers):
    """GET /browse/artist/{source}/{id} should return artist details."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_artist_details = AsyncMock(return_value=MOCK_ARTIST)

        response = await client.get(
            "/api/v1/browse/artist/deezer/27",
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Queen"


# --- Album Details Tests ---


@pytest.mark.asyncio
async def test_browse_album(client, admin_token_headers):
    """GET /browse/album/{source}/{id} should return album details."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_album_details = AsyncMock(return_value=MOCK_ALBUM)

        response = await client.get(
            "/api/v1/browse/album/deezer/456",
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "A Night at the Opera"


# --- Playlist Details Tests ---


@pytest.mark.asyncio
async def test_browse_playlist(client, admin_token_headers):
    """GET /browse/playlist/{source}/{id} should return playlist details."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_playlist_details = AsyncMock(return_value=MOCK_PLAYLIST)

        response = await client.get(
            "/api/v1/browse/playlist/deezer/789",
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Classic Rock"


@pytest.mark.asyncio
async def test_browse_search_with_type_album(client, admin_token_headers):
    """GET /browse/search?type=album should return album results."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.search_albums = AsyncMock(return_value=[MOCK_ALBUM])

        response = await client.get(
            "/api/v1/browse/search",
            params={"q": "A Night at the Opera", "type": "album"},
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "A Night at the Opera"


@pytest.mark.asyncio
async def test_browse_search_with_type_playlist(client, admin_token_headers):
    """GET /browse/search?type=playlist should return playlist results."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.search_tracks = AsyncMock(return_value=[MOCK_PLAYLIST])

        response = await client.get(
            "/api/v1/browse/search",
            params={"q": "Classic Rock", "type": "playlist"},
            headers=admin_token_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_browse_search_error_handling(client, admin_token_headers):
    """Search should return 500 when orchestrator fails."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.search_tracks = AsyncMock(side_effect=Exception("Internal error"))

        response = await client.get(
            "/api/v1/browse/search",
            params={"q": "error"},
            headers=admin_token_headers,
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal error"


@pytest.mark.asyncio
async def test_browse_playlist_not_found(client, admin_token_headers):
    """GET /browse/playlist/{source}/{id} should return 404 if not found."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_playlist_details = AsyncMock(return_value=None)

        response = await client.get(
            "/api/v1/browse/playlist/deezer/nonexistent",
            headers=admin_token_headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_browse_album_not_found(client, admin_token_headers):
    """GET /browse/album/{source}/{id} should return 404 if not found."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_album_details = AsyncMock(return_value=None)

        response = await client.get(
            "/api/v1/browse/album/deezer/nonexistent",
            headers=admin_token_headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_browse_artist_not_found(client, admin_token_headers):
    """GET /browse/artist/{source}/{id} should return 404 if not found."""
    with patch("app.api.v1.browse.search_orchestrator") as mock_orch:
        mock_orch.get_artist_details = AsyncMock(return_value=None)

        response = await client.get(
            "/api/v1/browse/artist/deezer/nonexistent",
            headers=admin_token_headers,
        )

    assert response.status_code == 404
