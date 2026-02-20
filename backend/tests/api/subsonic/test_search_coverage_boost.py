"""
Coverage boost for Subsonic search handlers.
Targets: search, search2, search3 with various parameters and edge cases.
"""

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
async def test_legacy_search_variants(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Setup data
    track = Track(id=uuid.uuid4(), title="UniqueSong", artist="UniqueArtist", album="UniqueAlbum")
    db_session.add(track)
    await db_session.flush()
    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/u.mp3")
    db_session.add(dl)
    await db_session.commit()

    # Search by title
    params = {**subsonic_auth_params, "title": "UniqueSong"}
    res = await client.get("/rest/search.view", params=params)
    assert len(res.json()["subsonic-response"]["searchResult"]["match"]) == 1

    # Search by artist
    params = {**subsonic_auth_params, "artist": "UniqueArtist"}
    res = await client.get("/rest/search.view", params=params)
    assert len(res.json()["subsonic-response"]["searchResult"]["match"]) == 1

    # Search by album
    params = {**subsonic_auth_params, "album": "UniqueAlbum"}
    res = await client.get("/rest/search.view", params=params)
    assert len(res.json()["subsonic-response"]["searchResult"]["match"]) == 1

    # Empty query
    res = await client.get("/rest/search.view", params=subsonic_auth_params)
    assert res.json()["subsonic-response"]["searchResult"]["match"] == []

@pytest.mark.asyncio
async def test_search2_edge_cases(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Artist with images
    artist = Artist(id=uuid.uuid4(), name="Visual Search", images={"url": "http://img.jpg"})
    db_session.add(artist)
    
    # Album without artist
    album = Album(id=uuid.uuid4(), title="Orphan Search Album", artist_id=None)
    db_session.add(album)
    
    # Track for artist to make them searchable in search2 (which joins tracks)
    t = Track(id=uuid.uuid4(), title="SearchTrack", artist_id=artist.id, album_id=album.id)
    db_session.add(t)
    await db_session.flush()
    
    dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path="/tmp/s.mp3")
    db_session.add(dl)
    await db_session.commit()

    # Search artists
    params = {**subsonic_auth_params, "query": "Visual", "albumCount": 0, "songCount": 0}
    res = await client.get("/rest/search2.view", params=params)
    data = res.json()["subsonic-response"]["searchResult2"]
    assert data["artist"][0]["coverArt"] is not None

    # Search albums (orphan)
    params = {**subsonic_auth_params, "query": "Orphan", "artistCount": 0, "songCount": 0}
    res = await client.get("/rest/search2.view", params=params)
    data = res.json()["subsonic-response"]["searchResult2"]
    assert data["album"][0]["artist"] == "Unknown Artist"

@pytest.mark.asyncio
async def test_search3_variants(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Create track/album/artist
    artist = Artist(id=uuid.uuid4(), name="Search3 Artist")
    album = Album(id=uuid.uuid4(), title="Search3 Album", artist_id=artist.id, release_date="2022-01-01")
    track = Track(id=uuid.uuid4(), title="Search3 Song", artist_id=artist.id, album_id=album.id, duration_ms=300000)
    db_session.add_all([artist, album, track])
    await db_session.flush()
    
    dl = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/s3.mp3")
    db_session.add(dl)
    await db_session.commit()

    # Search all
    params = {**subsonic_auth_params, "query": "Search3"}
    res = await client.get("/rest/search3.view", params=params)
    data = res.json()["subsonic-response"]["searchResult3"]
    assert len(data["artist"]) == 1
    assert len(data["album"]) == 1
    assert len(data["song"]) == 1
    assert data["album"][0]["duration"] == 300 # 300000ms / 1000
