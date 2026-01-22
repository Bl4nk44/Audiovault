"""
Extended tests for Subsonic user handlers to increase code coverage.
Covers: star/unstar, ratings, scrobble, now playing, random songs.
"""
import pytest
import uuid
from datetime import datetime, UTC
from httpx import AsyncClient
from app.models.artist import Artist
from app.models.album import Album
from app.models.track import Track
from app.models.download import Download
from app.models.starred import StarredTrack, StarredAlbum, StarredArtist


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
# Star / Unstar
# =============================================================================

@pytest.mark.asyncio
async def test_star_track_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test starring a track."""
    track = Track(id=uuid.uuid4(), title="Star Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/s.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_star_album_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test starring an album."""
    artist = Artist(id=uuid.uuid4(), name="Star Album Artist Ext")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Star Album Ext", artist_id=artist.id)
    db_session.add(album)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "albumId": str(album.id)}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_star_artist_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test starring an artist."""
    artist = Artist(id=uuid.uuid4(), name="Star Artist Ext")
    db_session.add(artist)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "artistId": str(artist.id)}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_star_multiple_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test starring multiple items at once."""
    track1 = Track(id=uuid.uuid4(), title="Multi Star 1 Ext")
    track2 = Track(id=uuid.uuid4(), title="Multi Star 2 Ext")
    db_session.add_all([track1, track2])
    await db_session.flush()
    
    for t in [track1, track2]:
        download = Download(track_id=t.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/{t.id}.mp3")
        db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": [str(track1.id), str(track2.id)]}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unstar_track_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test unstarring a track."""
    track = Track(id=uuid.uuid4(), title="Unstar Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    # First star it
    starred = StarredTrack(user_id=admin_user.id, track_id=track.id)
    db_session.add(starred)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/unstar.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_unstar_album_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test unstarring an album."""
    artist = Artist(id=uuid.uuid4(), name="Unstar Album Artist Ext")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Unstar Album Ext", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()
    
    starred = StarredAlbum(user_id=admin_user.id, album_id=album.id)
    db_session.add(starred)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "albumId": str(album.id)}
    response = await client.get("/rest/unstar.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unstar_artist_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test unstarring an artist."""
    artist = Artist(id=uuid.uuid4(), name="Unstar Artist Ext")
    db_session.add(artist)
    await db_session.flush()
    
    starred = StarredArtist(user_id=admin_user.id, artist_id=artist.id)
    db_session.add(starred)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "artistId": str(artist.id)}
    response = await client.get("/rest/unstar.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_star_invalid_id_ext(client: AsyncClient, subsonic_auth_params):
    """Test starring with invalid ID."""
    params = {**subsonic_auth_params, "id": "not-a-uuid"}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200


# =============================================================================
# getStarred / getStarred2
# =============================================================================

@pytest.mark.asyncio
async def test_get_starred_with_items(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getting starred items with data."""
    track = Track(id=uuid.uuid4(), title="Starred Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/st.mp3")
    db_session.add(download)
    
    starred = StarredTrack(user_id=admin_user.id, track_id=track.id)
    db_session.add(starred)
    await db_session.commit()
    
    response = await client.get("/rest/getStarred.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "starred" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_starred2_with_items(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getting starred items (ID3 format) with data."""
    track = Track(id=uuid.uuid4(), title="Starred2 Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/st2.mp3")
    db_session.add(download)
    
    starred = StarredTrack(user_id=admin_user.id, track_id=track.id)
    db_session.add(starred)
    await db_session.commit()
    
    response = await client.get("/rest/getStarred2.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "starred2" in data["subsonic-response"]


# =============================================================================
# setRating
# =============================================================================

@pytest.mark.asyncio
async def test_set_rating_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test setting a rating on a track."""
    track = Track(id=uuid.uuid4(), title="Rate Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/r.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id), "rating": 5}
    response = await client.get("/rest/setRating.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_set_rating_zero_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test clearing a rating (setting to 0)."""
    track = Track(id=uuid.uuid4(), title="Unrate Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/u.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id), "rating": 0}
    response = await client.get("/rest/setRating.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_set_rating_invalid_id_ext(client: AsyncClient, subsonic_auth_params):
    """Test setting rating on non-existent track."""
    params = {**subsonic_auth_params, "id": str(uuid.uuid4()), "rating": 3}
    response = await client.get("/rest/setRating.view", params=params)
    assert response.status_code == 200


# =============================================================================
# Scrobble
# =============================================================================

@pytest.mark.asyncio
async def test_scrobble_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test scrobbling a track."""
    track = Track(id=uuid.uuid4(), title="Scrobble Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/sc.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id), "submission": "true"}
    response = await client.get("/rest/scrobble.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_scrobble_now_playing_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test scrobble as now-playing (not full scrobble)."""
    track = Track(id=uuid.uuid4(), title="Now Playing Track Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/np.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": str(track.id), "submission": "false"}
    response = await client.get("/rest/scrobble.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_scrobble_with_time_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test scrobble with timestamp."""
    track = Track(id=uuid.uuid4(), title="Timed Scrobble Ext")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/ts.mp3")
    db_session.add(download)
    await db_session.commit()
    
    timestamp = int(datetime.now(UTC).timestamp() * 1000)
    params = {**subsonic_auth_params, "id": str(track.id), "time": timestamp}
    response = await client.get("/rest/scrobble.view", params=params)
    assert response.status_code == 200


# =============================================================================
# getNowPlaying
# =============================================================================

@pytest.mark.asyncio
async def test_get_now_playing_ext(client: AsyncClient, subsonic_auth_params):
    """Test getting now playing list."""
    response = await client.get("/rest/getNowPlaying.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert "nowPlaying" in data["subsonic-response"]


# =============================================================================
# getRandomSongs
# =============================================================================

@pytest.mark.asyncio
async def test_get_random_songs_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test getting random songs."""
    for i in range(5):
        track = Track(id=uuid.uuid4(), title=f"Random Track {i} Ext")
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/r{i}.mp3")
        db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "size": 3}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "randomSongs" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_random_songs_with_genre_ext(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test random songs filtered by genre."""
    track = Track(id=uuid.uuid4(), title="Genre Track Ext", metadata_content={"genre": "Jazz"})
    db_session.add(track)
    await db_session.flush()
    
    download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path="/tmp/g.mp3")
    db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "genre": "Jazz"}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_random_songs_with_size_limit(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    """Test random songs with size limit."""
    for i in range(10):
        track = Track(id=uuid.uuid4(), title=f"Size Track {i} Ext")
        db_session.add(track)
        await db_session.flush()
        download = Download(track_id=track.id, user_id=admin_user.id, status="completed", file_path=f"/tmp/s{i}.mp3")
        db_session.add(download)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "size": 5}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200
