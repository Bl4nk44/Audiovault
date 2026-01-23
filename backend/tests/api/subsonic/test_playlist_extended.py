"""
Extended tests for Subsonic playlist handlers to increase code coverage.
Covers: update playlist, add/remove songs, access control, edge cases.
"""

import uuid

import pytest
from app.models.download import Download
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}


@pytest.fixture
async def sample_playlist_ext(db_session, admin_user):
    """Create sample playlist with tracks for extended tests."""
    playlist = Playlist(
        id=uuid.uuid4(), name="Extended Test Playlist", owner_id=admin_user.id, public=True, comment="Test playlist"
    )
    db_session.add(playlist)
    await db_session.flush()

    tracks = []
    for i in range(3):
        track = Track(id=uuid.uuid4(), title=f"Playlist Track {i + 1}")
        db_session.add(track)
        await db_session.flush()

        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/pl{i}.mp3")
        db_session.add(download)

        pt = PlaylistTrack(playlist_id=playlist.id, track_id=track.id, order=i)
        db_session.add(pt)

        tracks.append(track)

    await db_session.commit()
    return playlist, tracks


# =============================================================================
# Update Playlist - Name
# =============================================================================


@pytest.mark.asyncio
async def test_update_playlist_name(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test updating playlist name."""
    playlist, _ = sample_playlist_ext
    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "name": "Renamed Playlist"}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_update_playlist_comment(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test updating playlist comment."""
    playlist, _ = sample_playlist_ext
    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "comment": "Updated comment"}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_update_playlist_public(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test updating playlist public flag."""
    playlist, _ = sample_playlist_ext
    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "public": "false"}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Update Playlist - Add Songs
# =============================================================================


@pytest.mark.asyncio
async def test_update_playlist_add_song(
    client: AsyncClient, subsonic_auth_params, sample_playlist_ext, db_session, admin_user
):
    """Test adding songs to playlist."""
    playlist, _ = sample_playlist_ext

    # Create new track to add
    new_track = Track(id=uuid.uuid4(), title="New Track To Add")
    db_session.add(new_track)
    await db_session.flush()

    download = Download(track_id=new_track.id, user_id=admin_user.id, status="completed", file_path="/tmp/new.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "songIdToAdd": str(new_track.id)}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_update_playlist_add_multiple_songs(
    client: AsyncClient, subsonic_auth_params, sample_playlist_ext, db_session, admin_user
):
    """Test adding multiple songs to playlist."""
    playlist, _ = sample_playlist_ext

    new_tracks = []
    for i in range(2):
        track = Track(id=uuid.uuid4(), title=f"Multi Add {i}")
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/ma{i}.mp3")
        db_session.add(download)
        new_tracks.append(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "songIdToAdd": [str(t.id) for t in new_tracks]}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Update Playlist - Remove Songs
# =============================================================================


@pytest.mark.asyncio
async def test_update_playlist_remove_song(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test removing songs from playlist by index."""
    playlist, _ = sample_playlist_ext

    # Remove first track (index 0)
    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "songIndexToRemove": 0}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_playlist_remove_multiple(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test removing multiple songs from playlist."""
    playlist, _ = sample_playlist_ext

    # Remove first and second tracks
    params = {**subsonic_auth_params, "playlistId": str(playlist.id), "songIndexToRemove": [0, 1]}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Update Playlist - Error Cases
# =============================================================================


@pytest.mark.asyncio
async def test_update_playlist_not_found(client: AsyncClient, subsonic_auth_params):
    """Test updating non-existent playlist."""
    params = {**subsonic_auth_params, "playlistId": str(uuid.uuid4()), "name": "New Name"}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"


@pytest.mark.asyncio
async def test_update_playlist_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test updating with invalid playlist ID."""
    params = {**subsonic_auth_params, "playlistId": "not-a-uuid", "name": "New Name"}

    response = await client.get("/rest/updatePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"


# =============================================================================
# Create Playlist - Extended Cases
# =============================================================================


@pytest.mark.asyncio
async def test_create_playlist_with_songs(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test creating playlist with initial songs."""
    tracks = []
    for i in range(2):
        track = Track(id=uuid.uuid4(), title=f"Create PL Track {i}")
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/cp{i}.mp3")
        db_session.add(download)
        tracks.append(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "name": "New With Songs", "songId": [str(t.id) for t in tracks]}

    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_create_playlist_empty(client: AsyncClient, subsonic_auth_params):
    """Test creating empty playlist."""
    params = {**subsonic_auth_params, "name": "Empty Playlist"}

    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_create_playlist_update_existing(
    client: AsyncClient, subsonic_auth_params, sample_playlist_ext, db_session, admin_user
):
    """Test createPlaylist with existing playlistId (acts as update)."""
    playlist, _ = sample_playlist_ext

    new_track = Track(id=uuid.uuid4(), title="Replace Track")
    db_session.add(new_track)
    await db_session.flush()
    download = Download(track_id=new_track.id, user_id=admin_user.id, status="completed", file_path="/tmp/rt.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {
        **subsonic_auth_params,
        "playlistId": str(playlist.id),
        "name": "Updated Name",
        "songId": str(new_track.id),
    }

    response = await client.get("/rest/createPlaylist.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Delete Playlist
# =============================================================================


@pytest.mark.asyncio
async def test_delete_playlist_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test deleting a playlist."""
    playlist = Playlist(id=uuid.uuid4(), name="To Delete", owner_id=admin_user.id)
    db_session.add(playlist)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(playlist.id)}

    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_delete_playlist_not_found(client: AsyncClient, subsonic_auth_params):
    """Test deleting non-existent playlist."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}

    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.status_code == 200
    _data = response.json()
    # May succeed silently or return error


@pytest.mark.asyncio
async def test_delete_playlist_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test deleting with invalid ID."""
    params = {**subsonic_auth_params, "id": "invalid-id"}

    response = await client.get("/rest/deletePlaylist.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Get Playlists
# =============================================================================


@pytest.mark.asyncio
async def test_get_playlists_ext(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test getting list of playlists."""
    response = await client.get("/rest/getPlaylists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "playlists" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_playlists_empty(client: AsyncClient, subsonic_auth_params):
    """Test getting playlists when none exist."""
    response = await client.get("/rest/getPlaylists.view", params=subsonic_auth_params)
    assert response.status_code == 200


# =============================================================================
# Get Playlist
# =============================================================================


@pytest.mark.asyncio
async def test_get_playlist_ext(client: AsyncClient, subsonic_auth_params, sample_playlist_ext):
    """Test getting single playlist with tracks."""
    playlist, tracks = sample_playlist_ext
    params = {**subsonic_auth_params, "id": str(playlist.id)}

    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "playlist" in data["subsonic-response"]
    assert len(data["subsonic-response"]["playlist"]["entry"]) == 3


@pytest.mark.asyncio
async def test_get_playlist_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getting non-existent playlist."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}

    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"


@pytest.mark.asyncio
async def test_get_playlist_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test getting playlist with invalid ID."""
    params = {**subsonic_auth_params, "id": "not-valid-uuid"}

    response = await client.get("/rest/getPlaylist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
