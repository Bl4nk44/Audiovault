import uuid

import pytest
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}

@pytest.mark.asyncio
async def test_get_music_folders(client: AsyncClient, subsonic_auth_params):
    """Test get_music_folders coverage."""
    response = await client.get("/rest/getMusicFolders.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "musicFolders" in data["subsonic-response"]
    assert data["subsonic-response"]["musicFolders"]["musicFolder"][0]["id"] == "1"

@pytest.mark.asyncio
async def test_get_artist_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test get_artist with invalid UUID."""
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200 # Subsonic returns 200 but with error in body
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient, subsonic_auth_params):
    """Test get_artist with non-existent UUID."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getArtist.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_get_album_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test get_album with invalid UUID."""
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getAlbum.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_get_album_not_found(client: AsyncClient, subsonic_auth_params):
    """Test get_album with non-existent UUID."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getAlbum.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_get_song_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test get_song with invalid UUID."""
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getSong.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_get_song_not_found(client: AsyncClient, subsonic_auth_params):
    """Test get_song with non-existent UUID."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getSong.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_get_music_directory_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test get_music_directory with invalid UUID (not '1' and not UUID)."""
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70 # Note: code 70 for not found in browse.py:511

@pytest.mark.asyncio
async def test_get_music_directory_root_visibility(client: AsyncClient, subsonic_auth_params, db_session):
    """Test getMusicDirectory root with an artist that has no images."""
    artist = Artist(id=uuid.uuid4(), name="No Image Artist", images=None)
    db_session.add(artist)
    await db_session.flush()

    # Must have a track to be visible (due to group_by Artist.id and join with Track)
    track = Track(id=uuid.uuid4(), title="T", artist_id=artist.id)
    db_session.add(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": "1"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    artists = data["subsonic-response"]["directory"]["child"]
    vis_artist = next(a for a in artists if a["title"] == "No Image Artist")
    assert vis_artist["coverArt"] is None # Covers line 492: "coverArt": f"ar-{artist.id}" if artist.images else None,

@pytest.mark.asyncio
async def test_get_music_directory_album_with_no_artist_obj(
    client: AsyncClient, subsonic_auth_params, db_session, admin_user
):
    """Test getMusicDirectory for an album with an artist_id that doesn't exist in DB."""
    non_existent_artist_id = uuid.uuid4()
    album = Album(id=uuid.uuid4(), title="Orphan Album", artist_id=non_existent_artist_id)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Orphan Track", album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/orphan.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["directory"]["artist"] == "Unknown Artist" # Covers line 586 (via 580)
    assert data["subsonic-response"]["directory"]["parent"] == "1" # Covers line 581

@pytest.mark.asyncio
async def test_get_album_with_no_artist_obj(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getAlbum for an album with an artist_id that doesn't exist in DB."""
    non_existent_artist_id = uuid.uuid4()
    album = Album(id=uuid.uuid4(), title="Orphan Album 2", artist_id=non_existent_artist_id)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Orphan Track 2", album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/orphan2.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["album"]["artist"] == "Unknown Artist" # Covers line 352 (via 347)

@pytest.mark.asyncio
async def test_get_indexes_full(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test get_indexes with real data to cover 87-128."""
    artist = Artist(id=uuid.uuid4(), name="The Beat")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track 1", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(
        track_id=track.id,
        user_id=admin_user.id,
        status="completed",
        file_path="/tmp/test.mp3"
    )
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "index" in data["subsonic-response"]["indexes"]
    assert len(data["subsonic-response"]["indexes"]["index"]) > 0
    assert data["subsonic-response"]["indexes"]["index"][0]["artist"][0]["name"] == "The Beat"

@pytest.mark.asyncio
async def test_get_artists_full(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test get_artists with real data to cover 155-205."""
    artist = Artist(id=uuid.uuid4(), name="Artists Test")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track ART", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(
        track_id=track.id,
        user_id=admin_user.id,
        status="completed",
        file_path="/tmp/art.mp3"
    )
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getArtists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "index" in data["subsonic-response"]["artists"]
    assert len(data["subsonic-response"]["artists"]["index"]) > 0
    assert data["subsonic-response"]["artists"]["index"][0]["artist"][0]["name"] == "Artists Test"

@pytest.mark.asyncio
async def test_get_music_directory_artist_and_album(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test get_music_directory with Artist and Album IDs to cover 515-622."""
    artist = Artist(id=uuid.uuid4(), name="Directory Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="Directory Album", artist_id=artist.id, release_date="2024-01-01")
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Directory Track", artist_id=artist.id, album_id=album.id, duration_ms=1000)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/dt.mp3")
    db_session.add(download)
    await db_session.commit()

    # Artist view
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["directory"]["child"][0]["title"] == "Directory Album"

    # Album view
    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["directory"]["child"][0]["title"] == "Directory Track"
