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
async def test_search2_comprehensive(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test search2 with all types of matches."""
    # Setup Artist, Album, Track + Download
    artist = Artist(id=uuid.uuid4(), name="MatchedArtist", images={"url": "http://img.jpg"})
    album = Album(id=uuid.uuid4(), title="MatchedAlbum", artist_id=artist.id, release_date="2020-01-01")
    track = Track(
        id=uuid.uuid4(),
        title="MatchedSong",
        artist_id=artist.id,
        album_id=album.id,
        artist="MatchedArtist",
        album="MatchedAlbum",
    )
    db_session.add_all([artist, album, track])
    await db_session.flush()

    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/m.mp3")
    db_session.add(dl)
    await db_session.commit()

    # 1. Match everything
    params = {**subsonic_auth_params, "query": "Matched"}
    resp = await client.get("/rest/search2.view", params=params)
    assert resp.status_code == 200
    data = resp.json()["subsonic-response"]["searchResult2"]
    assert len(data["artist"]) == 1
    assert len(data["album"]) == 1
    assert len(data["song"]) == 1
    assert data["album"][0]["year"] == 2020

    # 2. Match only artist
    params["query"] = "Artist"
    resp = await client.get("/rest/search2.view", params=params)
    data = resp.json()["subsonic-response"]["searchResult2"]
    assert len(data["artist"]) == 1
    # Depending on implementation, songs/albums might match if they have "Artist" in title
    # but here they are "MatchedAlbum" and "MatchedSong".
    # Wait, the album's artist name is "MatchedArtist", which contains "Artist".
    # Search2 album search uses Album.title only? Let's check search.py.
    # search2 albums: func.lower(Album.title).like(search_term) -> No artist name check!
    assert len(data["album"]) == 0


@pytest.mark.asyncio
async def test_search3_comprehensive(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test search3 with all types of matches and duration."""
    artist = Artist(id=uuid.uuid4(), name="Search3Artist")
    album = Album(id=uuid.uuid4(), title="Search3Album", artist_id=artist.id, release_date="2021-05-05")
    track = Track(id=uuid.uuid4(), title="Search3Song", artist_id=artist.id, album_id=album.id, duration_ms=120000)
    db_session.add_all([artist, album, track])
    await db_session.flush()

    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/s3.mp3")
    db_session.add(dl)
    await db_session.commit()

    params = {**subsonic_auth_params, "query": "Search3"}
    resp = await client.get("/rest/search3.view", params=params)
    assert resp.status_code == 200
    data = resp.json()["subsonic-response"]["searchResult3"]
    assert len(data["artist"]) == 1
    assert len(data["album"]) == 1
    assert len(data["song"]) == 1
    assert data["album"][0]["duration"] == 120  # 120000 / 1000


@pytest.mark.asyncio
async def test_search_legacy_newer_than(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test search.view (legacy) with newerThan and any."""
    track = Track(id=uuid.uuid4(), title="LegacySong", artist="LegacyArtist", album="LegacyAlbum")
    db_session.add(track)
    await db_session.flush()
    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/l.mp3")
    db_session.add(dl)
    await db_session.commit()

    # Search with 'any'
    params = {**subsonic_auth_params, "any": "Legacy"}
    resp = await client.get("/rest/search.view", params=params)
    assert len(resp.json()["subsonic-response"]["searchResult"]["match"]) == 1

    # Search with 'newerThan' (doesn't change SQL yet in implementation, but good to test param)
    params = {**subsonic_auth_params, "title": "Legacy", "newerThan": 123456789}
    resp = await client.get("/rest/search.view", params=params)
    assert len(resp.json()["subsonic-response"]["searchResult"]["match"]) == 1


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient, subsonic_auth_params):
    """Test search endpoints with no results."""
    params = {**subsonic_auth_params, "query": "NonExistent"}

    # search2
    resp = await client.get("/rest/search2.view", params=params)
    data = resp.json()["subsonic-response"]["searchResult2"]
    assert data["artist"] == []
    assert data["album"] == []
    assert data["song"] == []

    # search3
    resp = await client.get("/rest/search3.view", params=params)
    data = resp.json()["subsonic-response"]["searchResult3"]
    assert data["artist"] == []
    assert data["album"] == []
    assert data["song"] == []

    # legacy
    params_legacy = {**subsonic_auth_params, "title": "NonExistent"}
    resp = await client.get("/rest/search.view", params=params_legacy)
    assert resp.json()["subsonic-response"]["searchResult"]["match"] == []
