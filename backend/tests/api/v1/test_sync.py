import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_sync_manager():
    with patch("app.api.v1.sync.sync_manager") as mock:
        mock.analyze_watchlist = AsyncMock()
        mock.execute_sync = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_analyze_sync_success(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.analyze_watchlist.return_value = {
        "sync_token": "tok123",
        "to_remove": [],
        "warnings": [],
    }
    response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sync_token"] == "tok123"


@pytest.mark.asyncio
async def test_analyze_sync_not_found(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.analyze_watchlist.side_effect = ValueError("Watchlist not found")
    response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)
    assert response.status_code == 404
    assert "Watchlist not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_sync_server_error(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.analyze_watchlist.side_effect = RuntimeError("DB error")
    response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_execute_sync_missing_token(client, admin_token_headers):
    watchlist_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/sync/{watchlist_id}/execute",
        json={"approved_removals": []},
        headers=admin_token_headers,
    )
    assert response.status_code == 400
    assert "sync_token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_sync_success(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.execute_sync.return_value = {"removed": 2, "status": "done"}
    response = await client.post(
        f"/api/v1/sync/{watchlist_id}/execute",
        json={"sync_token": "tok123", "approved_removals": [str(uuid.uuid4())]},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"


@pytest.mark.asyncio
async def test_execute_sync_value_error(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.execute_sync.side_effect = ValueError("Invalid token")
    response = await client.post(
        f"/api/v1/sync/{watchlist_id}/execute",
        json={"sync_token": "bad_tok", "approved_removals": []},
        headers=admin_token_headers,
    )
    assert response.status_code == 400
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_sync_server_error(client, admin_token_headers, mock_sync_manager):
    watchlist_id = uuid.uuid4()
    mock_sync_manager.execute_sync.side_effect = RuntimeError("Unexpected")
    response = await client.post(
        f"/api/v1/sync/{watchlist_id}/execute",
        json={"sync_token": "tok123", "approved_removals": []},
        headers=admin_token_headers,
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_sync_requires_auth(client):
    watchlist_id = uuid.uuid4()
    response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze")
    assert response.status_code == 401
