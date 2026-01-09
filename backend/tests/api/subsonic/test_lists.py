
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.track import Track
from app.models.artist import Artist
from app.models.album import Album
from app.models.download import Download
from app.core.security import get_password_hash

@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass"),
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def sample_tracks(db_session: AsyncSession, test_user: User):
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    tracks = []
    for i in range(5):
        track = Track(
            title=f"Song {i}",
            artist_id=artist.id,
            album_id=album.id,
            metadata_content={"genre": "Rock" if i % 2 == 0 else "Jazz"}
        )
        tracks.append(track)
        db_session.add(track)
        await db_session.flush() # Flush to get track.id

        # Add Download
        download = Download(
            track_id=track.id,
            user_id=test_user.id,
            status="completed",
            file_path=f"/tmp/test_song_{i}.mp3"
        )
        db_session.add(download)
    
    await db_session.commit()
    return tracks

@pytest.mark.asyncio
async def test_get_genres(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getGenres.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    genres = data["subsonic-response"]["genres"]["genre"]
    assert len(genres) == 2
    genre_names = [g["value"] for g in genres]
    assert "Rock" in genre_names
    assert "Jazz" in genre_names

@pytest.mark.asyncio
async def test_get_album_list_2(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getAlbumList2.view?type=newest&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "albumList2" in data["subsonic-response"]
    assert len(data["subsonic-response"]["albumList2"]["album"]) > 0

@pytest.mark.asyncio
async def test_get_random_songs(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getRandomSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "randomSongs" in data["subsonic-response"]
    assert len(data["subsonic-response"]["randomSongs"]["song"]) > 0
