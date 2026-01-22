import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_spotify_service():
    with patch("app.api.v1.spotify.SpotifyService") as mock:
        instance = mock.return_value
        instance.client = MagicMock()
        instance.search.return_value = {"tracks": {"items": []}}
        instance.get_track.return_value = {"id": "123", "name": "Fake Track"}
        yield instance

@pytest.mark.asyncio
async def test_search_spotify(client: AsyncClient, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/search?q=test", headers=admin_token_headers)
    assert response.status_code == 200
    assert "tracks" in response.json()

@pytest.mark.asyncio
async def test_get_spotify_track(client: AsyncClient, admin_token_headers, mock_spotify_service):
    response = await client.get("/api/v1/spotify/track/123", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Fake Track"

@pytest.mark.asyncio
async def test_spotify_not_configured(client: AsyncClient, admin_token_headers):
    with patch("app.api.v1.spotify.SpotifyService") as mock:
        instance = mock.return_value
        instance.client = None # Service not configured
        response = await client.get("/api/v1/spotify/search?q=test", headers=admin_token_headers)
        assert response.status_code == 503
        assert response.json()["detail"] == "Spotify service not configured"
