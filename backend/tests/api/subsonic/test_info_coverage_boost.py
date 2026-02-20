import uuid
import pytest
from app.models.artist import Artist
from app.models.track import Track
from httpx import AsyncClient

@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}

@pytest.mark.asyncio
async def test_info_artist_invalid_id(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/getArtistInfo.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_info_artist_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getArtistInfo.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_info_artist_with_images(client: AsyncClient, subsonic_auth_params, db_session):
    artist = Artist(id=uuid.uuid4(), name="Image Artist", images=[{"url": "test"}])
    db_session.add(artist)
    await db_session.commit()
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getArtistInfo.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "largeImageUrl" in data["subsonic-response"]["artistInfo"]

@pytest.mark.asyncio
async def test_info_artist2_invalid_id(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/getArtistInfo2.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_info_artist2_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getArtistInfo2.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_info_artist2_with_images(client: AsyncClient, subsonic_auth_params, db_session):
    artist = Artist(id=uuid.uuid4(), name="Image Artist 2", images=[{"url": "test"}])
    db_session.add(artist)
    await db_session.commit()
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getArtistInfo2.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "largeImageUrl" in data["subsonic-response"]["artistInfo2"]

@pytest.mark.asyncio
async def test_similar_songs2_invalid_id(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 10

@pytest.mark.asyncio
async def test_similar_songs2_not_found(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "failed"
    assert response.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_similar_songs2_artist_id(client: AsyncClient, subsonic_auth_params, db_session):
    artist = Artist(id=uuid.uuid4(), name="Artist Directly")
    db_session.add(artist)
    await db_session.commit()
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

@pytest.mark.asyncio
async def test_get_newest_podcasts_endpoint(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getNewestPodcasts.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

@pytest.mark.asyncio
async def test_get_bookmarks_endpoint(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getBookmarks.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

@pytest.mark.asyncio
async def test_get_internet_radio_stations_endpoint(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getInternetRadioStations.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"
