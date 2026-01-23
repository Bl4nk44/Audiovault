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
    response = await client.get("/rest/getMusicFolders.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["musicFolders"]["musicFolder"][0]["name"] == "Music Library"


@pytest.mark.asyncio
async def test_get_indexes(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Setup data: Artist with completed download
    artist = Artist(id=uuid.uuid4(), name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track 1", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/test.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    # Check if artist is in index
    found = False
    for idx in data["subsonic-response"]["indexes"]["index"]:
        for art in idx["artist"]:
            if art["name"] == "Test Artist":
                found = True
                break
    assert found


@pytest.mark.asyncio
async def test_get_music_directory_root(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Root directory (id="1") should return list of artists
    artist = Artist(id=uuid.uuid4(), name="Dir Artist")
    db_session.add(artist)
    await db_session.flush()

    # Needs a track to be visible in some views
    track = Track(id=uuid.uuid4(), title="Dir Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": "1"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    children = data["subsonic-response"]["directory"]["child"]
    assert any(c["title"] == "Dir Artist" for c in children)


@pytest.mark.asyncio
async def test_get_music_directory_artist(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Artist Dir")
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="Album Dir", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track Dir", artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/dir.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    children = data["subsonic-response"]["directory"]["child"]
    assert any(c["title"] == "Album Dir" for c in children)


@pytest.mark.asyncio
async def test_get_artist_details(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Details Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="Details Album", artist_id=artist.id, release_date="2024-01-01")
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Details Track", artist_id=artist.id, album_id=album.id, duration_ms=100000)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/details.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["artist"]["name"] == "Details Artist"
    assert data["subsonic-response"]["artist"]["album"][0]["name"] == "Details Album"


@pytest.mark.asyncio
async def test_get_album(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Album Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="Full Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Full Track", artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/full.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["album"]["name"] == "Full Album"
    assert data["subsonic-response"]["album"]["song"][0]["title"] == "Full Track"


@pytest.mark.asyncio
async def test_get_song(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    track = Track(id=uuid.uuid4(), title="Single Song")
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/single.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/getSong.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["song"]["title"] == "Single Song"
