import uuid

import pytest
from app.models.playlist import Playlist, PlaylistTrack
from app.models.playlist_version import PlaylistVersion
from app.models.track import Track
from sqlalchemy import select


@pytest.fixture
async def sample_playlist(db_session, admin_user):
    playlist = Playlist(name="Test Playlist", owner_id=admin_user.id, public=False)
    db_session.add(playlist)
    await db_session.commit()
    await db_session.refresh(playlist)
    return playlist


@pytest.fixture
async def sample_track(db_session):
    track = Track(id=uuid.uuid4(), title="Test Song", artist="Artist")
    db_session.add(track)
    await db_session.commit()
    return track


@pytest.mark.asyncio
async def test_create_playlist(client, admin_token_headers):
    data = {"name": "New Playlist", "public": True, "comment": "Test"}
    response = await client.post("/api/v1/playlists/", json=data, headers=admin_token_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "New Playlist"
    assert response.json()["public"] is True


@pytest.mark.asyncio
async def test_get_playlists(client, admin_token_headers, sample_playlist):
    response = await client.get("/api/v1/playlists/", headers=admin_token_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id"] == str(sample_playlist.id)


@pytest.mark.asyncio
async def test_get_playlist_details(client, admin_token_headers, sample_playlist):
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_playlist.id)


@pytest.mark.asyncio
async def test_update_playlist(client, admin_token_headers, sample_playlist):
    data = {"name": "Updated Name", "public": False}
    response = await client.put(f"/api/v1/playlists/{sample_playlist.id}", json=data, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_playlist(client, admin_token_headers, sample_playlist, db_session):
    response = await client.delete(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers)
    assert response.status_code == 204
    # Verify
    assert await db_session.get(Playlist, sample_playlist.id) is None


@pytest.mark.asyncio
async def test_add_tracks_to_playlist(client, admin_token_headers, sample_playlist, sample_track, db_session):
    data = {"track_ids": [str(sample_track.id)]}
    response = await client.post(
        f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 201
    assert response.json()["added_count"] == 1


@pytest.mark.asyncio
async def test_remove_tracks_from_playlist(client, admin_token_headers, sample_playlist, sample_track, db_session):
    # Add track first
    pt = PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1)
    db_session.add(pt)
    await db_session.commit()

    data = {"track_ids": [str(sample_track.id)]}
    response = await client.request(
        "DELETE", f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_export_playlist(client, admin_token_headers, sample_playlist, sample_track, db_session):
    # Add track
    pt = PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1)
    db_session.add(pt)
    await db_session.commit()

    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/export", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["playlist"]["name"] == sample_playlist.name
    assert len(data["tracks"]) == 1


@pytest.mark.asyncio
async def test_playlist_versioning_flow(client, admin_token_headers, sample_playlist, sample_track, db_session):
    # 1. Create fake version directly for testing endpoint
    v = PlaylistVersion(
        playlist_id=sample_playlist.id,
        version_number=1,
        name="V1",
        change_type="create",
        tracks_snapshot=[{"track_id": str(sample_track.id), "order": 1}],
    )
    db_session.add(v)
    await db_session.commit()

    # Get versions
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/versions", headers=admin_token_headers)
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) >= 1
    assert versions[0]["version_number"] == 1

    # Rollback
    response = await client.post(f"/api/v1/playlists/{sample_playlist.id}/rollback/1", headers=admin_token_headers)
    assert response.status_code == 200
    assert "rolled back" in response.json()["message"]


@pytest.mark.asyncio
async def test_add_external_track_to_playlist(client, admin_token_headers, sample_playlist, db_session):
    # Test resolving "external:Artist:Title"
    data = {"track_ids": ["external:NewArtist:NewSong"]}
    response = await client.post(
        f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 201
    assert response.json()["added_count"] == 1

    # Verify track was created
    result = await db_session.execute(select(Track).where(Track.artist == "NewArtist", Track.title == "NewSong"))
    track = result.scalar_one_or_none()
    assert track is not None
    assert track.metadata_content["source"] == "lastfm"


@pytest.mark.asyncio
async def test_playlist_access_permissions(client, admin_token_headers, sample_playlist, normal_user_token_headers):
    # Normal user should not be able to see admin's private playlist
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}", headers=normal_user_token_headers)
    assert response.status_code == 404

    # Actually, let's just test that normal user can't delete it
    response = await client.delete(f"/api/v1/playlists/{sample_playlist.id}", headers=normal_user_token_headers)
    assert response.status_code == 404
