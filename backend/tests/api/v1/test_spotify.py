from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_spotify_service():
    with patch("app.api.v1.spotify.spotify_service") as mock_singleton:
        mock_singleton.search = AsyncMock(return_value={"tracks": {"items": [{"id": "s1"}]}})
        mock_singleton.get_playlist_details = AsyncMock(return_value={"id": "pl1", "name": "Spot PL"})
        mock_singleton.get_artist_details = AsyncMock(return_value={"id": "ar1", "name": "Artist"})
        mock_singleton.get_album_details = AsyncMock(return_value={"id": "al1", "name": "Album"})
        mock_singleton.get_track = AsyncMock(return_value={"id": "t1", "name": "Track"})
        yield mock_singleton


@pytest.mark.asyncio
async def test_search_spotify(client, admin_token_headers, mock_spotify_service):
    # Controller: return service.search(...) [Sync call inside async def]
    response = await client.get(
        "/api/v1/spotify/search", params={"q": "test", "limit": 10}, headers=admin_token_headers
    )

    assert response.status_code == 200
    mock_spotify_service.search.assert_called_with("test", 10, 0, "track")


@pytest.mark.asyncio
async def test_get_spotify_playlist(client, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/playlist/pl1", headers=admin_token_headers)
    assert response.status_code == 200
    mock_spotify_service.get_playlist_details.assert_called_with("pl1")


@pytest.mark.asyncio
async def test_get_spotify_artist(client, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/artist/ar1", headers=admin_token_headers)
    assert response.status_code == 200
    mock_spotify_service.get_artist_details.assert_called_with("ar1")


@pytest.mark.asyncio
async def test_get_spotify_album(client, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/album/al1", headers=admin_token_headers)
    assert response.status_code == 200
    mock_spotify_service.get_album_details.assert_called_with("al1")


@pytest.mark.asyncio
async def test_get_spotify_track(client, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/track/t1", headers=admin_token_headers)
    assert response.status_code == 200
    mock_spotify_service.get_track.assert_called_with("t1")
