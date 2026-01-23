"""
Tests for Watchlist API endpoints.
"""
import pytest
from httpx import AsyncClient
import uuid
from unittest.mock import AsyncMock, patch
from app.api.v1.watchlist import router

@pytest.mark.asyncio
async def test_add_to_watchlist(client: AsyncClient, admin_token_headers):
    payload = {
        "watch_type": "playlist",
        "source": "spotify",
        "source_id": "sp123",
        "source_name": "My Playlist",
        "auto_download": True
    }
    mock_item = {
        "id": str(uuid.uuid4()),
        "source_id": "sp123",
        "watch_type": "playlist"
    }
    
    with patch("app.api.v1.watchlist.watchlist_engine.add_to_watchlist", 
              new_callable=AsyncMock, return_value=mock_item):
        response = await client.post("/api/v1/watchlist/add", headers=admin_token_headers, json=payload)
        assert response.status_code == 200
        assert response.json()["source_id"] == "sp123"

@pytest.mark.asyncio
async def test_get_watchlist(client: AsyncClient, admin_token_headers):
    with patch("app.api.v1.watchlist.watchlist_engine.get_watchlist", 
              new_callable=AsyncMock, return_value=[]):
        response = await client.get("/api/v1/watchlist/list", headers=admin_token_headers)
        assert response.status_code == 200
        assert response.json() == []

@pytest.mark.asyncio
async def test_remove_from_watchlist_success(client: AsyncClient, admin_token_headers):
    watchlist_id = uuid.uuid4()
    with patch("app.api.v1.watchlist.watchlist_engine.remove_from_watchlist", 
              new_callable=AsyncMock, return_value=True):
        response = await client.delete(f"/api/v1/watchlist/remove/{watchlist_id}", headers=admin_token_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

@pytest.mark.asyncio
async def test_remove_from_watchlist_not_found(client: AsyncClient, admin_token_headers):
    watchlist_id = uuid.uuid4()
    with patch("app.api.v1.watchlist.watchlist_engine.remove_from_watchlist", 
              new_callable=AsyncMock, return_value=False):
        response = await client.delete(f"/api/v1/watchlist/remove/{watchlist_id}", headers=admin_token_headers)
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_watchlist_item_success(client: AsyncClient, admin_token_headers):
    watchlist_id = uuid.uuid4()
    payload = {"auto_download": False}
    mock_item = {"id": str(watchlist_id), "auto_download": False}
    
    with patch("app.api.v1.watchlist.watchlist_engine.update_watchlist_item", 
              new_callable=AsyncMock, return_value=mock_item):
        response = await client.patch(f"/api/v1/watchlist/{watchlist_id}", headers=admin_token_headers, json=payload)
        assert response.status_code == 200
        assert response.json()["auto_download"] == False

@pytest.mark.asyncio
async def test_update_watchlist_item_not_found(client: AsyncClient, admin_token_headers):
    watchlist_id = uuid.uuid4()
    payload = {"auto_download": False}
    
    with patch("app.api.v1.watchlist.watchlist_engine.update_watchlist_item", 
              new_callable=AsyncMock, return_value=None):
        response = await client.patch(f"/api/v1/watchlist/{watchlist_id}", headers=admin_token_headers, json=payload)
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_check_updates_trigger_api(client: AsyncClient, admin_token_headers):
    with patch("app.api.v1.watchlist.watchlist_engine.check_for_updates", 
              new_callable=AsyncMock, return_value=5):
        response = await client.post("/api/v1/watchlist/check-updates", headers=admin_token_headers)
        assert response.status_code == 200
        assert response.json()["new_downloads"] == 5
