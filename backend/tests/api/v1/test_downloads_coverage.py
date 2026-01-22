"""
Coverage tests for Downloads API.
"""
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.mark.asyncio
async def test_download_all_artist_tracks_success(client, admin_token_headers):
    artist_id = "spotify_artist_id"
    payload = {"source": "spotify"}
    
    mock_artist = {"name": "Test Artist"}
    mock_albums = [{"id": "album1"}, {"id": "album2"}]
    mock_tracks = [
        {"id": "t1", "title": "S1", "artist": "Test Artist", "duration_ms": 100},
        {"id": "t2", "title": "S2", "artist": "Test Artist", "duration_ms": 200}
    ]
    
    with patch("app.services.spotify_service.SpotifyService") as MockService:
        service_instance = MockService.return_value
        service_instance.client = True
        service_instance.get_artist_details.return_value = mock_artist
        service_instance.get_artist_albums.return_value = mock_albums
        service_instance.get_album_tracks.return_value = mock_tracks
        
        # Mock DB execute to return None (track doesn't exist)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        # We need to mock get_db to return our mock session which returns mock_result
        # The client fixture already overrides get_db but we need to control the session inside the endpoint
        # The endpoint uses `db.execute`. The client fixture uses `db_session`.
        # We can just rely on the real functional db provided by `client` + `db_session` fixture?
        # But `SpotifyService` is mocked inside the endpoint so we don't need real spotify.
        # Let's trust the `client` fixture handles DB.
        
        response = await client.post(
            f"/api/v1/downloads/artist/{artist_id}/download-all",
            headers=admin_token_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["queued_count"] == 4 # 2 albums * 2 tracks
        assert data["artist"] == "Test Artist"

@pytest.mark.asyncio
async def test_download_all_artist_tracks_invalid_source(client, admin_token_headers):
    response = await client.post(
        "/api/v1/downloads/artist/123/download-all",
        headers=admin_token_headers,
        json={"source": "unsupported"}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_remove_download_not_found(client, admin_token_headers):
    dl_id = str(uuid.uuid4())
    
    # Needs to mock DB returning None
    # We can rely on the fact that this UUID doesn't exist in the test DB
    response = await client.delete(
        f"/api/v1/downloads/{dl_id}",
        headers=admin_token_headers
    )
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_bulk_update_invalid_fields(client, admin_token_headers):
    payload = {
        "download_ids": [str(uuid.uuid4())],
        "updates": {"forbidden_field": "val"}
    }
    
    response = await client.put(
        "/api/v1/downloads/library/bulk-update",
        headers=admin_token_headers,
        json=payload
    )
    
    assert response.status_code == 400
    assert "Invalid fields" in response.json()["detail"]

@pytest.mark.asyncio
async def test_scan_library_access_denied(client, admin_token_headers):
    
    with patch("app.services.library_scanner.library_scanner_service.scan_directory",
              new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = {"status": "error", "message": "Access denied"}
        
        response = await client.post(
            "/api/v1/downloads/maintenance/scan-library",
            headers=admin_token_headers,
            json={"scan_path": "/root"} # query param
        )
        
        # Note: endpoint takes query param, but test client helper might need `params`
        # Using `client.post(..., params={...})`
        
        # Actually the signature is `scan_path: str | None = None`
        # In fastapi this is a query param
        
        response = await client.post(
            "/api/v1/downloads/maintenance/scan-library",
            headers=admin_token_headers,
            params={"scan_path": "/root"}
        )
        
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_download_album_not_found(client, admin_token_headers):
    album_id = "missing"
    payload = {"source": "spotify"}
    
    with patch("app.services.spotify_service.SpotifyService") as MockService:
        inst = MockService.return_value
        inst.client = True
        inst.get_album.return_value = None
        
        response = await client.post(
            f"/api/v1/downloads/album/{album_id}/download",
            headers=admin_token_headers,
            json=payload
        )
        
        assert response.status_code == 404
