import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def spotify_service_mock():
    with patch("app.services.spotify_service.SpotifyService") as mock_class:
        service_instance = mock_class.return_value
        service_instance.client = MagicMock()
        yield service_instance


@pytest.mark.asyncio
async def test_download_all_artist_tracks_success(
    client: AsyncClient, admin_token_headers, db_session, spotify_service_mock
):
    # Setup mocks
    artist_id = "artist123"
    spotify_service_mock.get_artist_details.return_value = {"name": "Test Artist"}
    spotify_service_mock.get_artist_albums.return_value = [{"id": "album1", "name": "Album 1"}]
    spotify_service_mock.get_album_tracks.return_value = [
        {
            "id": "track1",
            "title": "Track 1",
            "artist": "Test Artist",
            "duration_ms": 1000,
            "image_url": "http://img.com",
            "album": "Album 1",
            "isrc": "ISRC1",
        }
    ]

    with patch("app.api.v1.downloads.download_manager.add_download", new_callable=AsyncMock) as mock_add:
        payload = {"source": "spotify"}
        response = await client.post(
            f"/api/v1/downloads/artist/{artist_id}/download-all", headers=admin_token_headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["queued_count"] == 1
        assert mock_add.called


@pytest.mark.asyncio
async def test_download_album_success(client: AsyncClient, admin_token_headers, db_session, spotify_service_mock):
    # Setup mocks
    album_id = "album123"
    spotify_service_mock.get_album.return_value = {"name": "Test Album"}
    spotify_service_mock.get_album_tracks.return_value = [
        {
            "id": "track1",
            "title": "Track 1",
            "artist": "Test Artist",
            "duration_ms": 1000,
            "image_url": "http://img.com",
            "album": "Test Album",
            "isrc": "ISRC1",
        }
    ]

    with patch("app.api.v1.downloads.download_manager.add_download", new_callable=AsyncMock) as mock_add:
        payload = {"source": "spotify"}
        response = await client.post(
            f"/api/v1/downloads/album/{album_id}/download", headers=admin_token_headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["queued_count"] == 1
        assert mock_add.called


@pytest.mark.asyncio
async def test_bulk_update_library_items(client: AsyncClient, admin_token_headers, db_session, admin_user):
    track = Track(id=uuid.uuid4(), title="Bulk Track", artist="Artist", spotify_id="bulk_id")
    db_session.add(track)
    await db_session.flush()

    download = Download(id=uuid.uuid4(), user_id=admin_user.id, track_id=track.id, status="completed")
    db_session.add(download)
    await db_session.commit()

    payload = {"download_ids": [str(download.id)], "updates": {"artist": "Updated Artist", "genre": "Pop"}}

    # Mocking library_maintenance_service
    with patch(
        "app.services.library_maintenance.library_maintenance_service.update_download_item", new_callable=AsyncMock
    ) as mock_update:
        response = await client.put("/api/v1/downloads/library/bulk-update", headers=admin_token_headers, json=payload)

        assert response.status_code == 200
        assert response.json()["updated_count"] == 1
        assert mock_update.called


@pytest.mark.asyncio
async def test_scan_library_success(client: AsyncClient, admin_token_headers):
    with patch(
        "app.services.library_scanner.library_scanner_service.scan_directory", new_callable=AsyncMock
    ) as mock_scan:
        mock_scan.return_value = {"status": "success", "added": 5}
        response = await client.post(
            "/api/v1/downloads/maintenance/scan-library", headers=admin_token_headers, json={"scan_path": "/fake/path"}
        )
        assert response.status_code == 200
        assert response.json()["added"] == 5
