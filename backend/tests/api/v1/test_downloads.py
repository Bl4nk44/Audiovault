import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.models.download import Download
from app.models.track import Track
from sqlalchemy import select


@pytest.fixture
async def sample_download(db_session, admin_user):
    trk = Track(id=uuid.uuid4(), title="Test Track", artist="Test Artist", spotify_id="sp_123")
    db_session.add(trk)
    await db_session.flush()

    dl = Download(user_id=admin_user.id, track_id=trk.id, status="pending", source="spotify")
    db_session.add(dl)
    await db_session.commit()
    return dl


@pytest.mark.asyncio
async def test_get_downloads(client, admin_token_headers, sample_download):
    response = await client.get("/api/v1/downloads/queue", headers=admin_token_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id"] == str(sample_download.id)


@pytest.mark.asyncio
async def test_create_download(client, admin_token_headers):
    data = {"track_id": str(uuid.uuid4()), "source": "spotify", "playlist_name": "Test"}
    with patch("app.services.spotify_service.SpotifyService") as MockSpotify:  # noqa: N806
        mock_instance = MockSpotify.return_value
        mock_instance.get_track = AsyncMock(
            return_value={
                "title": "Test Title",
                "artist": "Test Artist",
                "duration_ms": 1000,
                "image_url": "http://example.com/img.jpg",
                "album": "Test Album",
                "isrc": "US123",
            }
        )

        response = await client.post("/api/v1/downloads/add", json=data, headers=admin_token_headers)
        assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_retry_download(client, admin_token_headers, sample_download, db_session):
    # Set status to failed
    sample_download.status = "failed"
    await db_session.commit()

    response = await client.post(f"/api/v1/downloads/{sample_download.id}/retry", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_delete_download(client, admin_token_headers, sample_download, db_session):
    response = await client.delete(f"/api/v1/downloads/{sample_download.id}", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bulk_update_downloads(client, admin_token_headers, sample_download, db_session):
    data = {"download_ids": [str(sample_download.id)], "updates": {"genre": "Rock", "artist": "Updated Artist"}}
    patch_target = "app.services.library_maintenance.library_maintenance_service.update_download_item"
    with patch(patch_target, new_callable=AsyncMock) as mock_update:
        response = await client.put("/api/v1/downloads/library/bulk-update", json=data, headers=admin_token_headers)
        assert response.status_code == 200
        assert response.json()["updated_count"] == 1
        assert mock_update.called


@pytest.mark.asyncio
async def test_bulk_update_invalid_fields(client, admin_token_headers, sample_download):
    data = {"download_ids": [str(sample_download.id)], "updates": {"invalid_field": "Hacker"}}
    response = await client.put("/api/v1/downloads/library/bulk-update", json=data, headers=admin_token_headers)
    assert response.status_code == 400
    assert "Invalid fields" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resolve_spotify_track(client, admin_token_headers, db_session):
    from app.api.v1.downloads import _resolve_track_to_local_id

    with patch("app.services.spotify_service.SpotifyService") as MockSpotify:  # noqa: N806
        mock_instance = MockSpotify.return_value
        mock_instance.get_track = AsyncMock(
            return_value={
                "title": "New Spotify Track",
                "artist": "Spotify Artist",
                "duration_ms": 200000,
                "image_url": "http://img.com",
                "album": "Spotify Album",
            }
        )

        track_uuid = await _resolve_track_to_local_id(db_session, "sp_new_123", "spotify")
        assert track_uuid is not None

        # Verify it was saved to DB
        result = await db_session.execute(select(Track).where(Track.id == track_uuid))
        track = result.scalar_one()
        assert track.title == "New Spotify Track"
        assert track.spotify_id == "sp_new_123"


@pytest.mark.asyncio
async def test_resolve_deezer_track(client, admin_token_headers, db_session):
    from app.api.v1.downloads import _resolve_track_to_local_id

    with patch("app.services.deezer_service.DeezerService") as MockDeezer:  # noqa: N806
        mock_instance = MockDeezer.return_value
        mock_instance.get_track = AsyncMock(
            return_value={
                "title": "Deezer Song",
                "artist": "Deezer Artist",
                "duration_ms": 180000,
                "image_url": "http://deezer.com/img",
                "album": "Deezer Album",
                "isrc": "FR123",
            }
        )

        track_uuid = await _resolve_track_to_local_id(db_session, "dz_456", "deezer")
        assert track_uuid is not None

        result = await db_session.execute(select(Track).where(Track.id == track_uuid))
        track = result.scalar_one()
        assert track.title == "Deezer Song"
        assert track.deezer_id == "dz_456"
