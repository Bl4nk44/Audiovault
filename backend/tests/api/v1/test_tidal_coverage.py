import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.dependencies import get_current_active_user
from app.main import app
from app.models.user import User
from httpx import AsyncClient


@pytest.fixture
def mock_user():
    user = User(id=uuid.uuid4(), username="testuser", email="test@example.com", hashed_password="pw", is_active=True)
    return user


@pytest.mark.asyncio
async def test_tidal_search_url_playlist(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        with patch("app.api.v1.tidal.tidal_service.get_playlist_info", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": "p123", "title": "Tidal Playlist"}

            response = await client.get("/api/v1/tidal/search", params={"q": "https://tidal.com/playlist/123"})
            assert response.status_code == 200
            assert response.json() == [{"id": "p123", "title": "Tidal Playlist"}]
    finally:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
async def test_tidal_search_tracks(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        with patch("app.api.v1.tidal.tidal_service.get_tracks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [{"id": "t1", "title": "Tidal Track"}]

            response = await client.get("/api/v1/tidal/search", params={"q": "https://tidal.com/track/1"})
            assert response.status_code == 200
            assert response.json() == [{"id": "t1", "title": "Tidal Track"}]
    finally:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
async def test_tidal_search_empty(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        response = await client.get("/api/v1/tidal/search", params={"q": "just search"})
        assert response.status_code == 200
        assert response.json() == []
    finally:
        del app.dependency_overrides[get_current_active_user]
