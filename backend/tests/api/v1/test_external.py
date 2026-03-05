from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def mock_spotify_service():
    with patch("app.api.v1.spotify.SpotifyService") as mock:
        instance = AsyncMock()
        mock.return_value = instance
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



