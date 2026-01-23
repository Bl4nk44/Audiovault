"""
Tests for Sync API endpoints.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_analyze_sync_success(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    mock_report = {"status": "ok", "safety_warning": False}

    with patch("app.api.v1.sync.sync_manager.analyze_watchlist", new_callable=AsyncMock, return_value=mock_report):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)

        assert response.status_code == 200
        assert response.json() == mock_report


@pytest.mark.asyncio
async def test_analyze_sync_not_found(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())

    with patch("app.api.v1.sync.sync_manager.analyze_watchlist", side_effect=ValueError("Watchlist not found")):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)

        assert response.status_code == 404
        assert "Watchlist not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_sync_success(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    payload = {"sync_token": "token123", "approved_removals": ["track1", "track2"]}
    mock_result = {"status": "success"}

    with patch("app.api.v1.sync.sync_manager.execute_sync", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/execute", headers=admin_token_headers, json=payload)

        assert response.status_code == 200
        assert response.json() == mock_result


@pytest.mark.asyncio
async def test_execute_sync_missing_token(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    payload = {"approved_removals": []}

    response = await client.post(f"/api/v1/sync/{watchlist_id}/execute", headers=admin_token_headers, json=payload)

    assert response.status_code == 400
    assert "Missing sync_token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_sync_invalid_token(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    payload = {"sync_token": "bad_token"}

    with patch("app.api.v1.sync.sync_manager.execute_sync", side_effect=ValueError("Invalid token")):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/execute", headers=admin_token_headers, json=payload)

        assert response.status_code == 400
        assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_sync_error(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    with patch("app.api.v1.sync.sync_manager.analyze_watchlist", side_effect=Exception("Unexpected boom")):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/analyze", headers=admin_token_headers)
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_execute_sync_error(client, admin_token_headers):
    watchlist_id = str(uuid.uuid4())
    payload = {"sync_token": "token123"}
    with patch("app.api.v1.sync.sync_manager.execute_sync", side_effect=Exception("Unexpected boom")):
        response = await client.post(f"/api/v1/sync/{watchlist_id}/execute", headers=admin_token_headers, json=payload)
        assert response.status_code == 500
