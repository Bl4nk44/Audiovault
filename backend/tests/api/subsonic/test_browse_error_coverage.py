"""
Coverage boost for Subsonic browse error paths and edge cases.
Targets: invalid IDs, missing items, and complex directory logic.
"""

import uuid

import pytest
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}


@pytest.mark.asyncio
async def test_browse_invalid_uuids(client: AsyncClient, auth_params):
    """Test endpoints with malformed UUIDs."""
    endpoints = ["/rest/getArtist.view", "/rest/getAlbum.view", "/rest/getSong.view", "/rest/getMusicDirectory.view"]

    for endpoint in endpoints:
        # "not-a-uuid" should trigger the ValueError in UUID(id)
        response = await client.get(endpoint, params={**auth_params, "id": "not-a-uuid"})
        assert response.status_code == 200
        data = response.json()["subsonic-response"]
        assert data["status"] == "failed"
        assert data["error"]["code"] in [10, 70]


@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient, auth_params):
    """Test getArtist with non-existent ID."""
    random_id = str(uuid.uuid4())
    response = await client.get("/rest/getArtist.view", params={**auth_params, "id": random_id})
    data = response.json()["subsonic-response"]
    assert data["status"] == "failed"
    assert data["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_album_not_found(client: AsyncClient, auth_params):
    """Test getAlbum with non-existent ID."""
    random_id = str(uuid.uuid4())
    response = await client.get("/rest/getAlbum.view", params={**auth_params, "id": random_id})
    data = response.json()["subsonic-response"]
    assert data["status"] == "failed"
    assert data["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_song_not_found(client: AsyncClient, auth_params):
    """Test getSong with non-existent ID."""
    random_id = str(uuid.uuid4())
    response = await client.get("/rest/getSong.view", params={**auth_params, "id": random_id})
    data = response.json()["subsonic-response"]
    assert data["status"] == "failed"
    assert data["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_music_directory_not_found(client: AsyncClient, auth_params):
    """Test getMusicDirectory with random UUID that is neither artist nor album."""
    random_id = str(uuid.uuid4())
    response = await client.get("/rest/getMusicDirectory.view", params={**auth_params, "id": random_id})
    data = response.json()["subsonic-response"]
    assert data["status"] == "failed"
    assert data["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_album_missing_artist(client: AsyncClient, auth_params, db_session, admin_user):
    """Test getAlbum where artist_id is null or artist is missing."""
    album = Album(id=uuid.uuid4(), title="Ghost Album", artist_id=None)
    db_session.add(album)
    await db_session.flush()

    # Add a track so it shows up
    track = Track(id=uuid.uuid4(), title="Track", album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/test.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getAlbum.view", params={**auth_params, "id": str(album.id)})
    data = response.json()["subsonic-response"]["album"]
    assert data["artist"] == "Unknown Artist"
    assert data["artistId"] is None


@pytest.mark.asyncio
async def test_get_music_directory_album_parent_logic(client: AsyncClient, auth_params, db_session, admin_user):
    """Test getMusicDirectory for album parent detection (with and without artist)."""
    # Case 1: Album with artist
    artist = Artist(id=uuid.uuid4(), name="Parent Artist")
    album1 = Album(id=uuid.uuid4(), title="Child Album 1", artist_id=artist.id)
    db_session.add_all([artist, album1])
    await db_session.flush()

    # Case 2: Album without artist
    album2 = Album(id=uuid.uuid4(), title="Child Album 2", artist_id=None)
    db_session.add(album2)
    await db_session.flush()

    for alb in [album1, album2]:
        t = Track(id=uuid.uuid4(), title="T", album_id=alb.id)
        db_session.add(t)
        await db_session.flush()
        dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{alb.id}.mp3")
        db_session.add(dl)

    await db_session.commit()

    # Verify Case 1
    resp1 = await client.get("/rest/getMusicDirectory.view", params={**auth_params, "id": str(album1.id)})
    dir1 = resp1.json()["subsonic-response"]["directory"]
    assert dir1["parent"] == str(artist.id)
    assert dir1["artist"] == "Parent Artist"

    # Verify Case 2
    resp2 = await client.get("/rest/getMusicDirectory.view", params={**auth_params, "id": str(album2.id)})
    dir2 = resp2.json()["subsonic-response"]["directory"]
    assert dir2["parent"] == "1"
    assert dir2["artist"] == "Unknown Artist"


@pytest.mark.asyncio
async def test_get_artists_view(client: AsyncClient, auth_params, db_session, admin_user):
    """Test getArtists.view which is similar to getIndexes but different endpoint."""
    artist = Artist(id=uuid.uuid4(), name="Artists View Artist")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Song", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/av.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getArtists.view", params=auth_params)
    assert response.status_code == 200
    data = response.json()["subsonic-response"]["artists"]
    assert any(idx["name"] == "A" for idx in data["index"])


@pytest.mark.asyncio
async def test_get_music_directory_album(client: AsyncClient, auth_params, db_session, admin_user):
    """Test getMusicDirectory for an album ID."""
    artist = Artist(id=uuid.uuid4(), name="Dir Alb Artist")
    album = Album(id=uuid.uuid4(), title="Dir Alb Album", artist_id=artist.id)
    db_session.add_all([artist, album])
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Dir Alb Track", album_id=album.id, artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/da.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getMusicDirectory.view", params={**auth_params, "id": str(album.id)})
    assert response.status_code == 200
    data = response.json()["subsonic-response"]["directory"]
    assert data["name"] == "Dir Alb Album"
    assert len(data["child"]) == 1
    assert data["child"][0]["title"] == "Dir Alb Track"
