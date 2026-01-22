"""
Extended tests for Subsonic lists handlers to increase code coverage.
Covers: getGenres, getAlbumList, getRandomSongs, getTopSongs, getSimilarSongs.
"""
import pytest
import uuid
from httpx import AsyncClient
from app.models.track import Track
from app.models.album import Album
from app.models.artist import Artist
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


@pytest.fixture
async def sample_library_ext(db_session, admin_user):
    """Create sample library with varied data."""
    # Create artists
    artist1 = Artist(id=uuid.uuid4(), name="Rock Artist")
    artist2 = Artist(id=uuid.uuid4(), name="Pop Artist")
    db_session.add_all([artist1, artist2])
    await db_session.flush()
    
    # Create albums
    album1 = Album(id=uuid.uuid4(), title="Rock Album 2023", artist_id=artist1.id, release_date="2023")
    album2 = Album(id=uuid.uuid4(), title="Pop Album 2024", artist_id=artist2.id, release_date="2024")
    db_session.add_all([album1, album2])
    await db_session.flush()
    
    # Create tracks with different genres
    tracks = []
    for i, (artist, album, genre) in enumerate([
        (artist1, album1, "Rock"),
        (artist1, album1, "Rock"),
        (artist2, album2, "Pop"),
    ]):
        track = Track(
            id=uuid.uuid4(),
            title=f"Track {i+1}",
            artist=artist.name,
            album=album.title,
            album_id=album.id,
            artist_id=artist.id,
            metadata_content={"genre": genre, "year": int(album.release_date)}
        )
        db_session.add(track)
        await db_session.flush()
        
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/t{i}.mp3")
        db_session.add(download)
        tracks.append(track)
    
    await db_session.commit()
    return {"artists": [artist1, artist2], "albums": [album1, album2], "tracks": tracks}


# =============================================================================
# Get Genres
# =============================================================================

@pytest.mark.asyncio
async def test_get_genres(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting all genres."""
    response = await client.get("/rest/getGenres.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_get_genres_empty(client: AsyncClient, subsonic_auth_params):
    """Test getting genres when library is empty."""
    response = await client.get("/rest/getGenres.view", params=subsonic_auth_params)
    assert response.status_code == 200


# =============================================================================
# Get Album List
# =============================================================================

@pytest.mark.asyncio
async def test_get_album_list_random(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting random album list."""
    params = {**subsonic_auth_params, "type": "random"}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_newest(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting newest albums."""
    params = {**subsonic_auth_params, "type": "newest"}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_alphabetical(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting albums alphabetically."""
    params = {**subsonic_auth_params, "type": "alphabeticalByName"}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_by_year(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting albums by year."""
    params = {**subsonic_auth_params, "type": "byYear", "fromYear": 2023, "toYear": 2024}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_by_genre(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting albums by genre."""
    params = {**subsonic_auth_params, "type": "byGenre", "genre": "Rock"}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_with_pagination(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test album list with pagination."""
    params = {**subsonic_auth_params, "type": "random", "size": 1, "offset": 0}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list_starred(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting starred albums."""
    params = {**subsonic_auth_params, "type": "starred"}
    response = await client.get("/rest/getAlbumList.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_album_list2_random(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getAlbumList2 endpoint."""
    params = {**subsonic_auth_params, "type": "random"}
    response = await client.get("/rest/getAlbumList2.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Get Random Songs
# =============================================================================

@pytest.mark.asyncio
async def test_get_random_songs(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting random songs."""
    params = {**subsonic_auth_params, "size": 5}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_random_songs_by_genre(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting random songs filtered by genre."""
    params = {**subsonic_auth_params, "genre": "Rock", "size": 10}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_random_songs_empty(client: AsyncClient, subsonic_auth_params):
    """Test getting random songs when library is empty."""
    response = await client.get("/rest/getRandomSongs.view", params=subsonic_auth_params)
    assert response.status_code == 200


# =============================================================================
# Get Top Songs
# =============================================================================

@pytest.mark.asyncio
async def test_get_top_songs(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting top songs."""
    params = {**subsonic_auth_params, "count": 10}
    response = await client.get("/rest/getTopSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_top_songs_by_artist(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting top songs by artist."""
    params = {**subsonic_auth_params, "artist": "Rock Artist", "count": 5}
    response = await client.get("/rest/getTopSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_top_songs_unknown_artist(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting top songs for unknown artist."""
    params = {**subsonic_auth_params, "artist": "Unknown Artist XYZ", "count": 5}
    response = await client.get("/rest/getTopSongs.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Get Similar Songs
# =============================================================================

@pytest.mark.asyncio
async def test_get_similar_songs(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getting similar songs."""
    track = sample_library_ext["tracks"][0]
    params = {**subsonic_auth_params, "id": str(track.id), "count": 5}
    response = await client.get("/rest/getSimilarSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_similar_songs_not_found(client: AsyncClient, subsonic_auth_params):
    """Test getting similar songs for non-existent track."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4()), "count": 5}
    response = await client.get("/rest/getSimilarSongs.view", params=params)
    assert response.status_code == 200
    # Should return error or empty


@pytest.mark.asyncio
async def test_get_similar_songs2(client: AsyncClient, subsonic_auth_params, sample_library_ext):
    """Test getSimilarSongs2 endpoint."""
    track = sample_library_ext["tracks"][0]
    params = {**subsonic_auth_params, "id": str(track.id), "count": 5}
    response = await client.get("/rest/getSimilarSongs2.view", params=params)
    assert response.status_code == 200
