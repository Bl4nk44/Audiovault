import uuid

import pytest
from httpx import AsyncClient

from app.models.playlist import Playlist
from app.models.track import Track


@pytest.fixture
async def sample_playlist(db_session, admin_user):
    playlist = Playlist(id=uuid.uuid4(), name="Source Playlist", owner_id=admin_user.id)
    db_session.add(playlist)
    await db_session.commit()
    await db_session.refresh(playlist)
    return playlist


@pytest.mark.asyncio
async def test_create_playlist(client: AsyncClient, admin_token_headers):
    payload = {"name": "New Test Playlist", "comment": "Automation Test"}
    response = await client.post("/api/v1/playlists/", headers=admin_token_headers, json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "New Test Playlist"


@pytest.mark.asyncio
async def test_get_playlists(client: AsyncClient, admin_token_headers, sample_playlist):
    response = await client.get("/api/v1/playlists/", headers=admin_token_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["name"] == sample_playlist.name


@pytest.mark.asyncio
async def test_update_playlist(client: AsyncClient, admin_token_headers, sample_playlist):
    payload = {"name": "Updated Name"}
    response = await client.put(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_add_tracks_to_playlist(client: AsyncClient, admin_token_headers, sample_playlist, db_session):
    # Create a track
    track = Track(id=uuid.uuid4(), title="Track for Playlist", spotify_id="pl_track_1")
    db_session.add(track)
    await db_session.commit()

    payload = {"track_ids": [str(track.id)]}
    response = await client.post(
        f"/api/v1/playlists/{sample_playlist.id}/tracks", headers=admin_token_headers, json=payload
    )
    assert response.status_code == 201
    assert response.json()["added_count"] == 1


@pytest.mark.asyncio
async def test_export_playlist(client: AsyncClient, admin_token_headers, sample_playlist):
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/export", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "playlist" in response.json()


@pytest.mark.asyncio
async def test_delete_playlist(client: AsyncClient, admin_token_headers, sample_playlist):
    response = await client.delete(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers)
    assert response.status_code == 204
