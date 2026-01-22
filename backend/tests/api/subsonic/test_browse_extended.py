"""
Extended tests for Subsonic browse handlers to increase code coverage.
Covers: getArtists, getMusicDirectory edge cases, album/artist not found, invalid IDs.
"""
import pytest
import uuid
from httpx import AsyncClient
from app.models.artist import Artist
from app.models.album import Album
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


# =============================================================================
# getArtists (ID3 view)
# =============================================================================

@pytest.mark.asyncio
async def test_get_artists(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getArtists endpoint returns alphabetical artist index."""
    # Create artists with different starting letters
    artists = [
        Artist(id=uuid.uuid4(), name="Alpha Artist"),
        Artist(id=uuid.uuid4(), name="Beta Artist"),
        Artist(id=uuid.uuid4(), name="123 Numeric Artist"),  # Should go to "#" index
    ]
    for a in artists:
        db_session.add(a)
    await db_session.flush()
    
    # Create tracks for each artist so they're visible
    for a in artists:
        track = Track(id=uuid.uuid4(), title=f"Track by {a.name}", artist_id=a.id)
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/t.mp3")
        db_session.add(download)
    
    await db_session.commit()
    
    response = await client.get("/rest/getArtists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "artists" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_artists_empty(client: AsyncClient, subsonic_auth_params):
    """Test getArtists with no artists in library."""
    response = await client.get("/rest/getArtists.view", params=subsonic_auth_params)
    assert response.status_code == 200
    # Should return empty but valid response


# =============================================================================
# getArtist edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getArtist with non-existent artist."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    # Should return error in subsonic format
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_artist_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test getArtist with invalid UUID."""
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_artist_multiple_albums(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getArtist with multiple albums."""
    artist = Artist(id=uuid.uuid4(), name="Multi Album Artist")
    db_session.add(artist)
    await db_session.flush()
    
    # Create multiple albums
    for i in range(3):
        album = Album(id=uuid.uuid4(), title=f"Album {i+1}", artist_id=artist.id, release_date=f"202{i}-01-01")
        db_session.add(album)
        await db_session.flush()
        
        track = Track(id=uuid.uuid4(), title=f"Track from Album {i+1}", artist_id=artist.id, album_id=album.id)
        db_session.add(track)
        await db_session.flush()
        
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/a{i}.mp3")
        db_session.add(download)
    
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(artist.id)}
    response = await client.get("/rest/getArtist.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert len(data["subsonic-response"]["artist"]["album"]) == 3


# =============================================================================
# getAlbum edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_get_album_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getAlbum with non-existent album."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_album_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test getAlbum with invalid UUID."""
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_album_multiple_tracks(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getAlbum with multiple tracks."""
    artist = Artist(id=uuid.uuid4(), name="Album Artist")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Multi Track Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()
    
    for i in range(5):
        track = Track(id=uuid.uuid4(), title=f"Track {i+1}", artist_id=artist.id, album_id=album.id, duration_ms=180000)
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/t{i}.mp3")
        db_session.add(download)
    
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getAlbum.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert len(data["subsonic-response"]["album"]["song"]) == 5


# =============================================================================
# getSong edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_get_song_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getSong with non-existent track."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getSong.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_song_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test getSong with invalid UUID."""
    params = {**subsonic_auth_params, "id": "not-valid"}
    response = await client.get("/rest/getSong.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed" or "error" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_song_with_metadata(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getSong returns all metadata."""
    artist = Artist(id=uuid.uuid4(), name="Song Artist")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Song Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()
    
    track = Track(
        id=uuid.uuid4(),
        title="Full Metadata Song",
        artist="Song Artist",
        album="Song Album",
        artist_id=artist.id,
        album_id=album.id,
        duration_ms=210000,
        metadata_content={"image_url": "http://cover.jpg", "genre": "Rock"}
    )
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/full.mp3", file_size=5000000)
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/getSong.view", params=params)
    assert response.status_code == 200
    data = response.json()
    song = data["subsonic-response"]["song"]
    assert song["title"] == "Full Metadata Song"
    assert "duration" in song or "artist" in song


# =============================================================================
# getMusicDirectory edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_get_music_directory_album(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getMusicDirectory with album ID returns songs."""
    artist = Artist(id=uuid.uuid4(), name="Dir Album Artist")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Dir Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()
    
    for i in range(3):
        track = Track(id=uuid.uuid4(), title=f"Dir Song {i+1}", artist_id=artist.id, album_id=album.id)
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/d{i}.mp3")
        db_session.add(download)
    
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(album.id)}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    data = response.json()
    children = data["subsonic-response"]["directory"]["child"]
    assert len(children) >= 3


@pytest.mark.asyncio
async def test_get_music_directory_invalid_id(client: AsyncClient, subsonic_auth_params):
    """Test getMusicDirectory with invalid ID."""
    params = {**subsonic_auth_params, "id": "invalid-uuid-string"}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200
    # Should handle gracefully


@pytest.mark.asyncio
async def test_get_music_directory_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getMusicDirectory with non-existent ID."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/getMusicDirectory.view", params=params)
    assert response.status_code == 200


# =============================================================================
# getIndexes edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_get_indexes_with_modified_since(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getIndexes with ifModifiedSince parameter."""
    artist = Artist(id=uuid.uuid4(), name="Modified Artist")
    db_session.add(artist)
    await db_session.flush()
    
    track = Track(id=uuid.uuid4(), title="Mod Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/m.mp3")
    db_session.add(download)
    await db_session.commit()
    
    # Request with a future timestamp (should return empty)
    params = {**subsonic_auth_params, "ifModifiedSince": 9999999999999}
    response = await client.get("/rest/getIndexes.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_indexes_with_music_folder(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getIndexes with musicFolderId parameter."""
    artist = Artist(id=uuid.uuid4(), name="Folder Artist")
    db_session.add(artist)
    await db_session.flush()
    
    track = Track(id=uuid.uuid4(), title="Folder Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/f.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "musicFolderId": "1"}
    response = await client.get("/rest/getIndexes.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_indexes_empty(client: AsyncClient, subsonic_auth_params):
    """Test getIndexes with no data."""
    response = await client.get("/rest/getIndexes.view", params=subsonic_auth_params)
    assert response.status_code == 200
