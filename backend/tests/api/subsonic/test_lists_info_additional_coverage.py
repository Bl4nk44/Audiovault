import pytest
import uuid
from httpx import AsyncClient
from app.models.track import Track
from app.models.download import Download
from app.models.artist import Artist
from app.models.album import Album
from datetime import datetime, timedelta, UTC

@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}

@pytest.mark.asyncio
async def test_get_genres_full(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getGenres.view with metadata extraction."""
    # Setup track with genre in metadata
    track = Track(
        id=uuid.uuid4(), 
        title="GenreSong", 
        metadata_content={"genre": "Synthwave"}
    )
    db_session.add(track)
    await db_session.flush()
    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/g.mp3")
    db_session.add(dl)
    await db_session.commit()

    resp = await client.get("/rest/getGenres.view", params=subsonic_auth_params)
    assert resp.status_code == 200
    data = resp.json()["subsonic-response"]["genres"]
    genres = data["genre"]
    assert any(g["value"] == "Synthwave" for g in genres)

@pytest.mark.asyncio
async def test_get_album_list_sorting(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getAlbumList.view with different sorting types."""
    # Setup albums with different titles and dates
    artist = Artist(id=uuid.uuid4(), name="Artist")
    a1 = Album(id=uuid.uuid4(), title="A_Album", artist_id=artist.id, created_at=datetime.now(UTC) - timedelta(days=1), release_date="2020-01-01")
    a2 = Album(id=uuid.uuid4(), title="B_Album", artist_id=artist.id, created_at=datetime.now(UTC), release_date="2021-01-01")
    db_session.add_all([artist, a1, a2])
    await db_session.flush()
    
    # Needs tracks/downloads for get_album_list to find them (it joins Download)
    t1 = Track(id=uuid.uuid4(), album_id=a1.id, title="T1")
    t2 = Track(id=uuid.uuid4(), album_id=a2.id, title="T2")
    db_session.add_all([t1, t2])
    await db_session.flush()
    
    dl1 = Download(track_id=t1.id, user_id=admin_user.id, status="completed", file_path="/tmp/t1.mp3")
    dl2 = Download(track_id=t2.id, user_id=admin_user.id, status="completed", file_path="/tmp/t2.mp3")
    db_session.add_all([dl1, dl2])
    await db_session.commit()

    # Alphabetical
    params = {**subsonic_auth_params, "type": "alphabetical"}
    resp = await client.get("/rest/getAlbumList.view", params=params)
    albums = resp.json()["subsonic-response"]["albumList2"]["album"]
    assert albums[0]["title"] == "A_Album"

    # Newest
    params["type"] = "newest"
    resp = await client.get("/rest/getAlbumList.view", params=params)
    albums = resp.json()["subsonic-response"]["albumList2"]["album"]
    assert albums[0]["title"] == "B_Album"

    # Random
    params["type"] = "random"
    resp = await client.get("/rest/getAlbumList.view", params=params)
    assert resp.status_code == 200

    # Recent (same as newest in implementation)
    params["type"] = "recent"
    resp = await client.get("/rest/getAlbumList.view", params=params)
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_top_similar_random_songs(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getTopSongs, getSimilarSongs and getRandomSongs."""
    artist = Artist(id=uuid.uuid4(), name="SimilarArt")
    t1 = Track(id=uuid.uuid4(), title="Song1", artist_id=artist.id, artist="SimilarArt")
    t2 = Track(id=uuid.uuid4(), title="Song2", artist_id=artist.id, artist="SimilarArt")
    db_session.add_all([artist, t1, t2])
    await db_session.flush()
    
    dl1 = Download(track_id=t1.id, user_id=admin_user.id, status="completed", file_path="/tmp/s1.mp3")
    dl2 = Download(track_id=t2.id, user_id=admin_user.id, status="completed", file_path="/tmp/s2.mp3")
    db_session.add_all([dl1, dl2])
    await db_session.commit()

    # Top Songs
    params = {**subsonic_auth_params, "artist": "SimilarArt"}
    resp = await client.get("/rest/getTopSongs.view", params=params)
    assert len(resp.json()["subsonic-response"]["topSongs"]["song"]) >= 1

    # Similar Songs (Legacy)
    params = {**subsonic_auth_params, "id": str(t1.id)}
    resp = await client.get("/rest/getSimilarSongs.view", params=params)
    assert len(resp.json()["subsonic-response"]["similarSongs"]["song"]) >= 1

    # Random Songs
    resp = await client.get("/rest/getRandomSongs.view", params=subsonic_auth_params)
    assert len(resp.json()["subsonic-response"]["randomSongs"]["song"]) >= 1

@pytest.mark.asyncio
async def test_get_artist_info_full(client: AsyncClient, subsonic_auth_params, db_session):
    """Test getArtistInfo and getArtistInfo2."""
    artist = Artist(id=uuid.uuid4(), name="BioArtist", bio="Best artist ever", images={"url": "http://img.jpg"})
    db_session.add(artist)
    await db_session.commit()

    # ArtistInfo (legacy)
    params = {**subsonic_auth_params, "id": str(artist.id)}
    resp = await client.get("/rest/getArtistInfo.view", params=params)
    data = resp.json()["subsonic-response"]["artistInfo"]
    assert data["biography"] == "Best artist ever"
    assert "largeImageUrl" in data

    # ArtistInfo2 (ID3)
    resp = await client.get("/rest/getArtistInfo2.view", params=params)
    data = resp.json()["subsonic-response"]["artistInfo2"]
    assert data["biography"] == "Best artist ever"

@pytest.mark.asyncio
async def test_get_similar_songs2(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getSimilarSongs2 by track and artist ID."""
    artist = Artist(id=uuid.uuid4(), name="SimilarArt2")
    t1 = Track(id=uuid.uuid4(), title="Track1", artist_id=artist.id)
    t2 = Track(id=uuid.uuid4(), title="Track2", artist_id=artist.id)
    db_session.add_all([artist, t1, t2])
    await db_session.flush()
    dl1 = Download(track_id=t1.id, user_id=admin_user.id, status="completed", file_path="/tmp/t1.mp3")
    dl2 = Download(track_id=t2.id, user_id=admin_user.id, status="completed", file_path="/tmp/t2.mp3")
    db_session.add_all([dl1, dl2])
    await db_session.commit()

    # SimilarSongs2 by Track ID
    params = {**subsonic_auth_params, "id": str(t1.id)}
    resp = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert len(resp.json()["subsonic-response"]["similarSongs2"]["song"]) >= 1

    # SimilarSongs2 by Artist ID
    params["id"] = str(artist.id)
    resp = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert len(resp.json()["subsonic-response"]["similarSongs2"]["song"]) >= 2

@pytest.mark.asyncio
async def test_info_errors(client: AsyncClient, subsonic_auth_params):
    """Test error handling in info endpoints."""
    # Invalid UUID
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    resp = await client.get("/rest/getArtistInfo.view", params=params)
    assert resp.json()["subsonic-response"]["status"] == "failed"
    assert resp.json()["subsonic-response"]["error"]["code"] == 10

    # Not found
    params["id"] = str(uuid.uuid4())
    resp = await client.get("/rest/getArtistInfo.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_get_album_list_extended(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test more album list types like byYear and starred."""
    artist = Artist(id=uuid.uuid4(), name="YearArt")
    a1 = Album(id=uuid.uuid4(), title="2010_Album", artist_id=artist.id, release_date="2010-01-01")
    db_session.add_all([artist, a1])
    await db_session.flush()
    t1 = Track(id=uuid.uuid4(), album_id=a1.id, title="Y1")
    db_session.add(t1)
    await db_session.flush()
    dl1 = Download(track_id=t1.id, user_id=admin_user.id, status="completed", file_path="/tmp/y1.mp3")
    db_session.add(dl1)
    await db_session.commit()

    # byYear
    params = {**subsonic_auth_params, "type": "byYear", "fromYear": 2000, "toYear": 2020}
    resp = await client.get("/rest/getAlbumList2.view", params=params)
    assert resp.status_code == 200

    # starred (fallback to newest)
    params["type"] = "starred"
    resp = await client.get("/rest/getAlbumList2.view", params=params)
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_similar_songs_errors(client: AsyncClient, subsonic_auth_params):
    """Test errors in getSimilarSongs."""
    # Invalid ID
    params = {**subsonic_auth_params, "id": "not-uuid"}
    resp = await client.get("/rest/getSimilarSongs.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 10

    # Not found
    params["id"] = str(uuid.uuid4())
    resp = await client.get("/rest/getSimilarSongs.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 70

@pytest.mark.asyncio
async def test_stubbed_endpoints(client: AsyncClient, subsonic_auth_params):
    """Test unimplemented stub endpoints."""
    # Podcasts
    resp = await client.get("/rest/getPodcasts.view", params=subsonic_auth_params)
    assert "podcasts" in resp.json()["subsonic-response"]

    # Bookmarks
    resp = await client.get("/rest/getBookmarks.view", params=subsonic_auth_params)
    assert "bookmarks" in resp.json()["subsonic-response"]

    # Radio
    resp = await client.get("/rest/getInternetRadioStations.view", params=subsonic_auth_params)
    assert "internetRadioStations" in resp.json()["subsonic-response"]
