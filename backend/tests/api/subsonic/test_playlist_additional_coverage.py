import uuid
import pytest
from httpx import AsyncClient
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User

@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}

@pytest.fixture
async def other_user(db_session):
    user = User(
        id=uuid.uuid4(),
        username="other_user",
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        subsonic_password="hashed_password",
        hashed_password="hashed_password",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_get_playlist_invalid_id_and_denied(client: AsyncClient, subsonic_auth_params, db_session, other_user):
    """Test getPlaylist with invalid ID and access denied."""
    # 1. Invalid ID
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["error"]["code"] == 10

    # 2. Access Denied (Private playlist of another user)
    private_pl = Playlist(id=uuid.uuid4(), name="Other Private", owner_id=other_user.id, public=False)
    db_session.add(private_pl)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(private_pl.id)}
    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["error"]["code"] == 50

@pytest.mark.asyncio
async def test_create_playlist_edge_cases(client: AsyncClient, subsonic_auth_params, db_session, other_user):
    """Test createPlaylist error paths and validation."""
    # 1. Update existing but wrong owner
    other_pl = Playlist(id=uuid.uuid4(), name="Other PL", owner_id=other_user.id)
    db_session.add(other_pl)
    await db_session.commit()

    params = {**subsonic_auth_params, "playlistId": str(other_pl.id), "name": "Hack"}
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 50

    # 2. Update with invalid UUID
    params = {**subsonic_auth_params, "playlistId": "invalid"}
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 10

    # 3. Create without name
    params = {**subsonic_auth_params} # No name, no playlistId
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 10

    # 4. Create with invalid song IDs (should be skipped)
    params = {**subsonic_auth_params, "name": "Skip Invalid", "songId": ["not-uuid-1", "not-uuid-2"]}
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.json()["subsonic-response"]["status"] == "ok"

@pytest.mark.asyncio
async def test_update_playlist_complex(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test complex updatePlaylist scenarios: removal by index and reordering."""
    # Create playlist with 3 tracks
    pl = Playlist(id=uuid.uuid4(), name="Complex Update", owner_id=admin_user.id)
    db_session.add(pl)
    await db_session.flush()

    tracks = []
    for i in range(3):
        t = Track(id=uuid.uuid4(), title=f"T{i}")
        db_session.add(t)
        await db_session.flush()
        pt = PlaylistTrack(playlist_id=pl.id, track_id=t.id, order=i)
        db_session.add(pt)
        tracks.append(t)
    await db_session.commit()

    # Add 1 song and remove index 1 (the second song)
    new_t = Track(id=uuid.uuid4(), title="New")
    db_session.add(new_t)
    await db_session.commit()

    params = {
        **subsonic_auth_params, 
        "playlistId": str(pl.id), 
        "songIdToAdd": str(new_t.id),
        "songIndexToRemove": [1]
    }
    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    
    # Verify contents via getPlaylist
    params_get = {**subsonic_auth_params, "id": str(pl.id)}
    resp_get = await client.get("/rest/getPlaylist.view", params=params_get)
    data = resp_get.json()
    entries = data["subsonic-response"]["playlist"]["entry"]
    assert len(entries) == 3 # 3 - 1 + 1 = 3
    assert entries[0]["title"] == "T0"
    assert entries[1]["title"] == "T2" 
    assert entries[2]["title"] == "New"

@pytest.mark.asyncio
async def test_get_playlists_visibility(client: AsyncClient, subsonic_auth_params, db_session, admin_user, other_user):
    """Test getPlaylists showing own and public ones."""
    # 1. Private by other
    other_private = Playlist(id=uuid.uuid4(), name="Other Private", owner_id=other_user.id, public=False)
    # 2. Public by other
    other_public = Playlist(id=uuid.uuid4(), name="Other Public", owner_id=other_user.id, public=True)
    # 3. Private by own (admin)
    own_private = Playlist(id=uuid.uuid4(), name="My Private", owner_id=admin_user.id, public=False)
    
    db_session.add_all([other_private, other_public, own_private])
    await db_session.commit()

    response = await client.get("/rest/getPlaylists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    pls = response.json()["subsonic-response"]["playlists"]["playlist"]
    pl_names = [p["name"] for p in pls]
    
    assert "My Private" in pl_names
    assert "Other Public" in pl_names
    assert "Other Private" not in pl_names

@pytest.mark.asyncio
async def test_update_playlist_visibility_change(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test toggling public flag in updatePlaylist."""
    pl = Playlist(id=uuid.uuid4(), name="Visibility Test", owner_id=admin_user.id, public=False)
    db_session.add(pl)
    await db_session.commit()

    # Change to public
    params = {**subsonic_auth_params, "playlistId": str(pl.id), "public": "true"}
    await client.get("/rest/updatePlaylist.view", params=params)
    
    # Verify
    await db_session.refresh(pl)
    assert pl.public is True

@pytest.mark.asyncio
async def test_create_playlist_with_invalid_existing_id(client: AsyncClient, subsonic_auth_params):
    """Test createPlaylist with non-existent playlistId."""
    params = {**subsonic_auth_params, "playlistId": str(uuid.uuid4()), "name": "Should Fail"}
    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_delete_playlist_not_found_handled(client: AsyncClient, subsonic_auth_params):
    """Test deletePlaylist with non-existent ID."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_delete_playlist_access_denied(client: AsyncClient, subsonic_auth_params, db_session, other_user):
    """Test access denied for deletePlaylist."""
    other_pl = Playlist(id=uuid.uuid4(), name="Other Private", owner_id=other_user.id, public=False)
    db_session.add(other_pl)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(other_pl.id)}
    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.json()["subsonic-response"]["error"]["code"] == 50
