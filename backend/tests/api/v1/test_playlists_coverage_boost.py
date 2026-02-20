"""
Coverage boost for V1 Playlists API.
Targets: external track resolution, duplicate handling, and edge cases in export/rollback.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.playlist import Playlist
from app.models.track import Track

@pytest.mark.asyncio
async def test_add_external_tracks_to_playlist(client, admin_token_headers, admin_user, db_session):
    # 1. Create a playlist owned by admin
    pl = Playlist(name="External Test", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.commit()
    await db_session.refresh(pl)

    # 2. Add tracks with external: format
    data = {
        "track_ids": [
            "external:Beatles:Yesterday",
            "external:Queen:Bohemian Rhapsody"
        ]
    }
    
    with patch("app.services.download_manager.download_manager.add_download", new_callable=AsyncMock) as mock_dl:
        response = await client.post(f"/api/v1/playlists/{pl.id}/tracks", json=data, headers=admin_token_headers)
        assert response.status_code == 201
        assert response.json()["added_count"] == 2
        assert mock_dl.call_count == 2

    # 3. Verify tracks were created in DB
    result = await db_session.execute(
        __import__("sqlalchemy").select(Track).where(Track.title == "Yesterday")
    )
    track = result.scalar_one_or_none()
    assert track is not None
    assert track.artist == "Beatles"

@pytest.mark.asyncio
async def test_add_external_track_existing(client, admin_token_headers, admin_user, db_session):
    # 1. Create a playlist and an existing track
    pl = Playlist(name="External Existing Test", owner_id=admin_user.id)
    track = Track(id=uuid.uuid4(), title="Existing Song", artist="Existing Artist")
    db_session.add_all([pl, track])
    await db_session.commit()
    await db_session.refresh(pl)

    # 2. Add track using external: format but it already exists in DB
    data = {
        "track_ids": [
            "external:Existing Artist:Existing Song"
        ]
    }
    
    with patch("app.services.download_manager.download_manager.add_download", new_callable=AsyncMock) as mock_dl:
        response = await client.post(f"/api/v1/playlists/{pl.id}/tracks", json=data, headers=admin_token_headers)
        assert response.status_code == 201
        assert response.json()["added_count"] == 1
        # Should NOT trigger new download as it's already there
        assert mock_dl.call_count == 0

@pytest.mark.asyncio
async def test_remove_tracks_invalid_uuids(client, admin_token_headers, admin_user, db_session):
    pl = Playlist(name="Invalid UUID Test", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.commit()
    await db_session.refresh(pl)

    # Send invalid UUID strings
    data = {"track_ids": ["not-a-uuid", "another-bad-one"]}
    response = await client.request("DELETE", f"/api/v1/playlists/{pl.id}/tracks", json=data, headers=admin_token_headers)
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_export_playlist_empty_name(client, admin_token_headers, admin_user, db_session):
    pl = Playlist(name="!!!", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.commit()
    await db_session.refresh(pl)

    response = await client.get(f"/api/v1/playlists/{pl.id}/export", headers=admin_token_headers)
    assert response.status_code == 200
    assert "attachment; filename" in response.headers["Content-Disposition"]
