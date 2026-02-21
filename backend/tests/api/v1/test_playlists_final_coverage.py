"""
Final coverage boost for V1 Playlists API.
Focuses on correct owner access for GET methods and track mapping.
"""

import uuid

import pytest
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track


@pytest.mark.asyncio
async def test_get_playlists_with_tracks_and_owner(client, admin_token_headers, admin_user, db_session):
    # 1. Setup: Create playlist owned by admin with a track
    pl = Playlist(name="Owner PL", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.flush()

    t = Track(id=uuid.uuid4(), title="Track 1", artist="Artist", duration_ms=1000)
    db_session.add(t)
    await db_session.flush()

    pt = PlaylistTrack(playlist_id=pl.id, track_id=t.id, order=1)
    db_session.add(pt)
    await db_session.commit()

    # 2. Test GET / (list)
    response = await client.get("/api/v1/playlists/", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(p["id"] == str(pl.id) for p in data)

    # 3. Test GET /{id} (details)
    response = await client.get(f"/api/v1/playlists/{pl.id}", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Owner PL"
    assert len(response.json()["tracks"]) == 1


@pytest.mark.asyncio
async def test_update_playlist_mapping_coverage(client, admin_token_headers, admin_user, db_session):
    pl = Playlist(name="Update Me", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.commit()

    # Update playlist - triggers reconstruct response
    data = {"name": "New Name", "public": True}
    response = await client.put(f"/api/v1/playlists/{pl.id}", json=data, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["public"] is True
