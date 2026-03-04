import uuid

import pytest
from app.api.subsonic.handlers.browse import (
    get_album,
    get_artist,
    get_artists,
    get_indexes,
    get_music_directory,
    get_music_folders,
    get_song,
)
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


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


@pytest.mark.asyncio
async def test_get_artists_id3(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="ID3 Artist")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="ID3 Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/id3.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getArtists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert any(idx["name"] == "I" for idx in data["subsonic-response"]["artists"]["index"])


@pytest.mark.asyncio
async def test_get_artist_invalid_id(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 10


@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_music_directory_invalid_id(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "not-uuid-or-1"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"


@pytest.mark.asyncio
async def test_get_indexes_non_alpha(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="123 Artist")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Numeric Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/num.mp3")
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    # Check if grouped under #
    found = False
    for idx in data["subsonic-response"]["indexes"]["index"]:
        if idx["name"] == "#":
            found = True
            break
    assert found


@pytest.mark.asyncio
async def test_get_music_directory_album(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Alb Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="Alb Dir Test", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Alb Song", artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/alb.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["directory"]["name"] == "Alb Dir Test"
    assert any(c["title"] == "Alb Song" for c in data["subsonic-response"]["directory"]["child"])


@pytest.mark.asyncio
async def test_get_album_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_song_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getSong.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"


@pytest.mark.asyncio
async def test_browse_handlers_explicit(db_session: AsyncSession, admin_user: User):
    # test get_music_folders
    resp = await get_music_folders(current_user=admin_user, db=db_session, f="json")
    assert resp["subsonic-response"]["musicFolders"]["musicFolder"][0]["name"] == "Music Library"

    # Setup data for others
    artist = Artist(id=uuid.uuid4(), name="Explicit Artist")
    db_session.add(artist)
    await db_session.flush()
    album = Album(id=uuid.uuid4(), title="Explicit Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()
    track = Track(id=uuid.uuid4(), title="Explicit Song", artist_id=artist.id, album_id=album.id, duration_ms=1000)
    db_session.add(track)
    await db_session.flush()
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/exp.mp3")
    db_session.add(download)
    await db_session.commit()

    # test get_indexes
    resp = await get_indexes(current_user=admin_user, db=db_session, f="json")
    assert any(idx["name"] == "E" for idx in resp["subsonic-response"]["indexes"]["index"])

    # test get_artists
    resp = await get_artists(current_user=admin_user, db=db_session, f="json")
    assert any(idx["name"] == "E" for idx in resp["subsonic-response"]["artists"]["index"])

    # test get_artist
    resp = await get_artist(id=str(artist.id), current_user=admin_user, db=db_session, f="json")
    assert resp["subsonic-response"]["artist"]["name"] == "Explicit Artist"

    # test get_album
    resp = await get_album(id=str(album.id), current_user=admin_user, db=db_session, f="json")
    assert resp["subsonic-response"]["album"]["name"] == "Explicit Album"

    # test get_song
    resp = await get_song(id=str(track.id), current_user=admin_user, db=db_session, f="json")
    assert resp["subsonic-response"]["song"]["title"] == "Explicit Song"

    # test get_music_directory (root)
    resp = await get_music_directory(id="1", current_user=admin_user, db=db_session, f="json")
    assert any(c["title"] == "Explicit Artist" for c in resp["subsonic-response"]["directory"]["child"])

    # test get_music_directory (artist)
    resp = await get_music_directory(id=str(artist.id), current_user=admin_user, db=db_session, f="json")
    assert any(c["title"] == "Explicit Album" for c in resp["subsonic-response"]["directory"]["child"])

    # test get_music_directory (album)
    resp = await get_music_directory(id=str(album.id), current_user=admin_user, db=db_session, f="json")
    assert any(c["title"] == "Explicit Song" for c in resp["subsonic-response"]["directory"]["child"])
