import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.dependencies import get_current_active_user
from app.main import app
from app.models.user import User
from httpx import AsyncClient


@pytest.fixture
def mock_user():
    return User(id=uuid.uuid4(), username="testuser", email="test@example.com", hashed_password="pw", is_active=True)


@pytest.mark.asyncio
async def test_downloads_add(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        # The endpoint expects DownloadRequest which has track_id and source
        with patch("app.api.v1.downloads._resolve_track_to_local_id", return_value=uuid.uuid4()):
            with patch("app.api.v1.downloads.download_manager.add_download", new_callable=AsyncMock) as m:
                m.return_value = {"id": "d1"}
                response = await client.post("/api/v1/downloads/add", json={"track_id": "t1", "source": "spotify"})
                assert response.status_code == 200
                assert response.json() == {"id": "d1"}
    finally:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
async def test_downloads_get_queue(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        with patch("app.services.library_data.library_data_service.get_queue_items", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get("/api/v1/downloads/queue")
            assert response.status_code == 200
            assert response.json() == []
    finally:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
async def test_downloads_restart_all(client: AsyncClient, mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = override_user

    try:
        with patch("app.api.v1.downloads.download_manager.restart_all_downloads", new_callable=AsyncMock) as m:
            m.return_value = 5
            response = await client.post("/api/v1/downloads/restart-all")
            assert response.status_code == 200
            assert response.json() == {"status": "success", "count": 5}
    finally:
        del app.dependency_overrides[get_current_active_user]
