from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_youtube_service():
    with patch("app.api.v1.youtube.YouTubeService") as mock_cls:
        service_instance = MagicMock()
        mock_cls.return_value = service_instance
        yield service_instance

@pytest.mark.asyncio
async def test_search_youtube(client, admin_token_headers, mock_youtube_service):
    mock_youtube_service.search.return_value = [{"id": "yt1", "title": "Video 1"}]

    response = await client.get(
        "/api/v1/youtube/search",
        params={"q": "test", "limit": 10},
        headers=admin_token_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "yt1"
    mock_youtube_service.search.assert_called_with("test", 10, "song")

@pytest.mark.asyncio
async def test_search_youtube_offset(client, admin_token_headers, mock_youtube_service):
    # Test offset > 0 returns empty list (implementation detail)
    response = await client.get(
        "/api/v1/youtube/search",
        params={"q": "test", "offset": 10},
        headers=admin_token_headers
    )
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_youtube_playlist(client, admin_token_headers, mock_youtube_service):
    mock_youtube_service.get_playlist_details.return_value = {"id": "pl1", "title": "My Playlist"}

    response = await client.get(
        "/api/v1/youtube/playlist/pl1",
        headers=admin_token_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "My Playlist"
    mock_youtube_service.get_playlist_details.assert_called_with("pl1")

@pytest.mark.asyncio
async def test_get_youtube_playlist_not_found(client, admin_token_headers, mock_youtube_service):
    mock_youtube_service.get_playlist_details.return_value = None

    response = await client.get(
        "/api/v1/youtube/playlist/bad_id",
        headers=admin_token_headers
    )

    assert response.status_code == 404
