"""
Coverage boost for Subsonic browse handlers.
Focuses on edge cases: XML format, missing names, non-alphabetical names, 
missing release dates, and unknown artists.
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
    # Use XML for some tests to boost coverage in subsonic_response
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "xml"}

@pytest.mark.asyncio
async def test_get_indexes_xml_and_edge_cases(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getIndexes with XML, non-alpha artist, and artist with empty name."""
    # Artist with empty name (should be skipped by browse.py logic)
    artist_empty_name = Artist(id=uuid.uuid4(), name="")
    # Artist with non-alpha name (should go to #)
    artist_hash = Artist(id=uuid.uuid4(), name="!!! Hash")
    
    db_session.add(artist_empty_name)
    db_session.add(artist_hash)
    await db_session.flush()

    for a in [artist_empty_name, artist_hash]:
        track = Track(id=uuid.uuid4(), title="Track", artist_id=a.id)
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{a.id}.mp3")
        db_session.add(download)
    
    await db_session.commit()

    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert "<?xml" in response.text
    assert "!!!" in response.text

@pytest.mark.asyncio
async def test_get_artist_no_release_date(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getArtist with album having no release date."""
    artist = Artist(id=uuid.uuid4(), name="No Date Artist", images={"url": "http://img.com"})
    db_session.add(artist)
    await db_session.flush()

    album = Album(id=uuid.uuid4(), title="No Date Album", artist_id=artist.id, release_date=None)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track", artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/nd.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(artist.id), "f": "json"}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["artist"]["album"][0]["year"] is None

@pytest.mark.asyncio
async def test_get_album_unknown_artist(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getAlbum where artist_id is None or artist not found."""
    album = Album(id=uuid.uuid4(), title="Orphan Album", artist_id=None)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Orphan Track", album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/orphan.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id), "f": "json"}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["album"]["artist"] == "Unknown Artist"

@pytest.mark.asyncio
async def test_get_music_directory_album_orphan(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getMusicDirectory for an album with no artist."""
    album = Album(id=uuid.uuid4(), title="Directory Orphan Album", artist_id=None)
    db_session.add(album)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Dir Orphan Track", album_id=album.id)
    db_session.add(track)
    await db_session.flush()

    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/do.mp3")
    db_session.add(download)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id), "f": "json"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["directory"]["artist"] == "Unknown Artist"

@pytest.mark.asyncio
async def test_get_music_directory_root_all_path(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getMusicDirectory root with an artist having images."""
    artist = Artist(id=uuid.uuid4(), name="Visual Artist", images={"url": "test"})
    db_session.add(artist)
    await db_session.flush()
    
    # Must have a track to be visible
    track = Track(id=uuid.uuid4(), title="T", artist_id=artist.id)
    db_session.add(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": "1", "f": "json"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    artists = data["subsonic-response"]["directory"]["child"]
    vis_artist = next(a for a in artists if a["title"] == "Visual Artist")
    assert vis_artist["coverArt"] is not None
