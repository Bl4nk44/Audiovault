import pytest
import uuid
from httpx import AsyncClient
from app.models.artist import Artist
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

@pytest.mark.asyncio
async def test_subsonic_get_artist_info(client: AsyncClient, subsonic_auth_params, db_session):
    artist = Artist(id=uuid.uuid4(), name="Info Artist", bio="Great biography")
    db_session.add(artist)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getArtistInfo.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["artistInfo"]["biography"] == "Great biography"

@pytest.mark.asyncio
async def test_subsonic_get_similar_songs2(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Similar Artist")
    db_session.add(artist)
    await db_session.flush()
    
    track = Track(id=uuid.uuid4(), title="Original Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()
    
    similar_track = Track(id=uuid.uuid4(), title="Similar Track", artist_id=artist.id)
    db_session.add(similar_track)
    await db_session.flush()
    
    download = Download(track_id=similar_track.id, user_id=admin_user.id, status="completed", file_path="/tmp/sim.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert any(s["title"] == "Similar Track" for s in data["subsonic-response"]["similarSongs2"]["song"])

@pytest.mark.asyncio
async def test_subsonic_get_podcasts(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getPodcasts.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert "podcasts" in response.json()["subsonic-response"]
