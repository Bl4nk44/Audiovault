import uuid

import pytest
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}


@pytest.mark.asyncio
async def test_album_list_types(client: AsyncClient, subsonic_auth, db_session):
    for type_param in ["frequent", "recent", "alphabetical", "byYear", "byGenre"]:
        params = {**subsonic_auth, "type": type_param}
        response = await client.get("/rest/getAlbumList.view", params=params)
        assert response.status_code == 200
        assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_album_list2_types(client: AsyncClient, subsonic_auth, db_session):
    for type_param in ["frequent", "recent", "alphabetical", "byYear", "byGenre"]:
        params = {**subsonic_auth, "type": type_param}
        response = await client.get("/rest/getAlbumList2.view", params=params)
        assert response.status_code == 200
        assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_random_songs_filters(client: AsyncClient, subsonic_auth, db_session):
    params = {**subsonic_auth, "fromYear": "2000", "toYear": "2020", "genre": "Rock"}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_top_songs_with_artist(client: AsyncClient, subsonic_auth, db_session):
    params = {**subsonic_auth, "artist": "Some Artist"}
    response = await client.get("/rest/getTopSongs.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_similar_songs_invalid_id(client: AsyncClient, subsonic_auth):
    params = {**subsonic_auth, "id": "invalid-uuid"}
    response = await client.get("/rest/getSimilarSongs.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["error"]["code"] == 10


@pytest.mark.asyncio
async def test_similar_songs_not_found(client: AsyncClient, subsonic_auth):
    params = {**subsonic_auth, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getSimilarSongs.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["error"]["code"] == 70


@pytest.mark.asyncio
async def test_similar_songs_found(client: AsyncClient, subsonic_auth, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Similar Artist List")
    db_session.add(artist)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Original Track List", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()

    similar_track = Track(id=uuid.uuid4(), title="Similar Track List", artist_id=artist.id)
    db_session.add(similar_track)
    await db_session.flush()

    download = Download(track_id=similar_track.id, user_id=admin_user.id, status="completed", file_path="/tmp/sim2.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth, "id": str(track.id)}
    response = await client.get("/rest/getSimilarSongs.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"
