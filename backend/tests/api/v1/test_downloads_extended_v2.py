import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def override_auth(db_session, admin_user):
    from app.core.dependencies import get_current_active_user
    from app.main import app

    async def get_admin():
        return admin_user

    app.dependency_overrides[get_current_active_user] = get_admin
    yield admin_user
    app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_download_artist_tracks_unsupported_source(client: AsyncClient, override_auth):
    artist_id = "test-artist"
    response = await client.post(f"/api/v1/downloads/artist/{artist_id}/download-all", json={"source": "unsupported"})
    assert response.status_code == 400
    assert "Only Spotify source" in response.text


@pytest.mark.asyncio
async def test_bulk_update_library_invalid_fields(client: AsyncClient, override_auth):
    payload = {"download_ids": [str(uuid.uuid4())], "updates": {"invalid_field": "val"}}
    response = await client.put("/api/v1/downloads/library/bulk-update", json=payload)
    assert response.status_code == 400
    assert "Invalid fields" in response.text


@pytest.mark.asyncio
async def test_bulk_update_library_empty(client: AsyncClient, override_auth):
    payload = {"download_ids": [], "updates": {"title": "new"}}
    response = await client.put("/api/v1/downloads/library/bulk-update", json=payload)
    assert response.status_code == 400
    assert "No items specified" in response.text


@pytest.mark.asyncio
async def test_maintenance_fix_legacy(client: AsyncClient, override_auth):
    with patch(
        "app.services.library_maintenance.library_maintenance_service.fix_legacy_data", new_callable=AsyncMock
    ) as mock_fix:
        mock_fix.return_value = 5
        response = await client.post("/api/v1/downloads/maintenance/fix-legacy-data")
        assert response.status_code == 200
        assert response.json()["fixed_count"] == 5


@pytest.mark.asyncio
async def test_scan_library_access_denied(client: AsyncClient, override_auth):
    with patch(
        "app.services.library_scanner.library_scanner_service.scan_directory", new_callable=AsyncMock
    ) as mock_scan:
        mock_scan.return_value = {"status": "error", "message": "Access denied to folder"}
        response = await client.post("/api/v1/downloads/maintenance/scan-library", params={"scan_path": "/restricted"})
        assert response.status_code == 403
        assert "Access denied" in response.text
