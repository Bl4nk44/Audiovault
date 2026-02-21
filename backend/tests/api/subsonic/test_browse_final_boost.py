"""
Final coverage boost for Subsonic browse handlers.
Targets: XML format, missing release dates, artists with/without images,
album year parsing, and directory structure edge cases.
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
    # Use XML to trigger XML serialization logic
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "xml"}

@pytest.mark.asyncio
async def test_get_indexes_xml_variations(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getIndexes with XML and various artist name types."""
    # Artist with name starting with number/symbol
    a1 = Artist(id=uuid.uuid4(), name="123 Numeric")
    # Artist with name starting with 'The' (logic might skip it or group it)
    a2 = Artist(id=uuid.uuid4(), name="The Beatles")

    db_session.add_all([a1, a2])
    await db_session.flush()

    for a in [a1, a2]:
        t = Track(id=uuid.uuid4(), title="Song", artist_id=a.id)
        db_session.add(t)
        await db_session.flush()
        dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{a.id}.mp3")
        db_session.add(dl)

    await db_session.commit()

    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert "<?xml" in response.text
    assert 'name="123 Numeric"' in response.text or 'name="Numeric"' in response.text
    assert "The Beatles" in response.text

@pytest.mark.asyncio
async def test_get_artist_details_with_and_without_dates(
    client: AsyncClient, subsonic_auth_params, db_session, admin_user
):
    """Test getArtist with various album data."""
    artist = Artist(id=uuid.uuid4(), name="Data Artist", images={"url": "test"})
    db_session.add(artist)
    await db_session.flush()

    # Album 1: Short release date
    alb1 = Album(id=uuid.uuid4(), title="Oldie", artist_id=artist.id, release_date="199") # Too short for year
    # Album 2: No release date
    alb2 = Album(id=uuid.uuid4(), title="Unknown Date", artist_id=artist.id, release_date=None)

    db_session.add_all([alb1, alb2])
    await db_session.flush()

    for alb in [alb1, alb2]:
        t = Track(id=uuid.uuid4(), title="Track", artist_id=artist.id, album_id=alb.id)
        db_session.add(t)
        await db_session.flush()
        dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{alb.id}.mp3")
        db_session.add(dl)

    await db_session.commit()

    # Use JSON for easy assertion
    params = {**subsonic_auth_params, "id": str(artist.id), "f": "json"}
    response = await client.get("/rest/getArtist.view", params=params)
    data = response.json()["subsonic-response"]["artist"]
    assert len(data["album"]) == 2
    # Verify year parsing fallback
    years = [a.get("year") for a in data["album"]]
    assert None in years

@pytest.mark.asyncio
async def test_get_album_with_track_indices(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getAlbum ensures track numbers are generated if missing."""
    artist = Artist(id=uuid.uuid4(), name="Indext Artist")
    album = Album(id=uuid.uuid4(), title="Index Album", artist_id=artist.id)
    db_session.add_all([artist, album])
    await db_session.flush()

    # Track with no metadata (no track number)
    t = Track(id=uuid.uuid4(), title="No Meta Track", artist_id=artist.id, album_id=album.id, metadata_content={})
    db_session.add(t)
    await db_session.flush()

    dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path="/tmp/nometa.mp3")
    db_session.add(dl)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(album.id), "f": "json"}
    response = await client.get("/rest/getAlbum.view", params=params)
    songs = response.json()["subsonic-response"]["album"]["song"]
    assert songs[0]["track"] == 1 # Fallback to index + 1

@pytest.mark.asyncio
async def test_get_music_directory_root_all_paths(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getMusicDirectory root covers all artist scenarios."""
    # Artist with images
    a1 = Artist(id=uuid.uuid4(), name="Visual", images={"profile": "url"})
    # Artist without images
    a2 = Artist(id=uuid.uuid4(), name="Plain", images=None)

    db_session.add_all([a1, a2])
    await db_session.flush()

    for a in [a1, a2]:
        t = Track(id=uuid.uuid4(), title="T", artist_id=a.id)
        db_session.add(t)
        await db_session.flush()
        dl = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{a.id}.mp3")
        db_session.add(dl)

    await db_session.commit()

    params = {**subsonic_auth_params, "id": "1", "f": "json"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    children = response.json()["subsonic-response"]["directory"]["child"]

    v_art = next(c for c in children if c["title"] == "Visual")
    p_art = next(c for c in children if c["title"] == "Plain")
    assert v_art["coverArt"] is not None
    assert p_art["coverArt"] is None
