import pytest
import uuid
from httpx import AsyncClient
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.download import Download

@pytest.fixture
def subsonic_auth_params(admin_user):
    return {
        "u": admin_user.username,
        "p": "admin",
        "c": "pytest",
        "v": "1.16.1",
        "f": "json"
    }

@pytest.fixture
async def sample_playlist(db_session, admin_user):
    playlist = Playlist(id=uuid.uuid4(), name="Subsonic PL", owner_id=admin_user.id)
    db_session.add(playlist)
    await db_session.flush()
    
    track = Track(id=uuid.uuid4(), title="PL Track", artist="PL Artist")
    db_session.add(track)
    await db_session.flush()
    
    pt = PlaylistTrack(playlist_id=playlist.id, track_id=track.id, order=0)
    db_session.add(pt)
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/pl.mp3")
    db_session.add(download)
    
    await db_session.commit()
    return playlist, track

@pytest.mark.asyncio
async def test_subsonic_get_playlists(client: AsyncClient, subsonic_auth_params, sample_playlist):
    _, _ = sample_playlist
    response = await client.get("/rest/getPlaylists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert len(data["subsonic-response"]["playlists"]["playlist"]) >= 1

@pytest.mark.asyncio
async def test_subsonic_get_playlist(client: AsyncClient, subsonic_auth_params, sample_playlist):
    playlist, _ = sample_playlist
    params = {**subsonic_auth_params, "id": str(playlist.id)}
    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["playlist"]["name"] == "Subsonic PL"
    assert len(data["subsonic-response"]["playlist"]["entry"]) >= 1

@pytest.mark.asyncio
async def test_subsonic_create_playlist(client: AsyncClient, subsonic_auth_params, db_session):
    track = Track(id=uuid.uuid4(), title="New PL Track")
    db_session.add(track)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "name": "Created PL", "songId": str(track.id)}
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

@pytest.mark.asyncio
async def test_subsonic_delete_playlist(client: AsyncClient, subsonic_auth_params, sample_playlist):
    playlist, _ = sample_playlist
    params = {**subsonic_auth_params, "id": str(playlist.id)}
    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"
