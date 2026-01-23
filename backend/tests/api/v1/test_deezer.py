from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_deezer_service():
    with patch("app.api.v1.deezer.DeezerService") as mock_cls:
        service_instance = MagicMock()
        # Mock methods as AsyncMock because they are awaited in the controller
        service_instance.search = AsyncMock()
        service_instance.get_playlist_details = AsyncMock()
        service_instance.get_artist_details = AsyncMock()

        mock_cls.return_value = service_instance
        yield service_instance

@pytest.mark.asyncio
async def test_search_deezer(client, admin_token_headers, mock_deezer_service):
    mock_deezer_service.search.return_value = [{"id": "dz1", "title": "Track 1"}]

    response = await client.get(
        "/api/v1/deezer/search",
        params={"q": "test", "limit": 10},
        headers=admin_token_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "dz1"
    mock_deezer_service.search.assert_called_with("test", 10, 0)

@pytest.mark.asyncio
async def test_get_deezer_playlist(client, admin_token_headers, mock_deezer_service):
    mock_deezer_service.get_playlist_details.return_value = {"id": "pl1", "title": "Deezer PL"}

    response = await client.get(
        "/api/v1/deezer/playlist/pl1",
        headers=admin_token_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Deezer PL"
    mock_deezer_service.get_playlist_details.assert_called_with("pl1")

@pytest.mark.asyncio
async def test_get_deezer_playlist_not_found(client, admin_token_headers, mock_deezer_service):
    mock_deezer_service.get_playlist_details.return_value = None

    response = await client.get(
        "/api/v1/deezer/playlist/bad_id",
        headers=admin_token_headers
    )

    assert response.status_code == 404
