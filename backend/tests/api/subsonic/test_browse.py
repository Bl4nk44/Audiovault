import pytest
from app.core.security import get_password_hash
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        username="testuser", email="test@example.com", hashed_password=get_password_hash("testpass"), is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_data(db_session: AsyncSession, test_user: User):
    artist = Artist(name="Test Artist", bio="Test description")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(title="Test Song", artist_id=artist.id, album_id=album.id, metadata_content={"genre": "Test Genre"})
    db_session.add(track)
    await db_session.flush()

    # Add Download
    download = Download(track_id=track.id, user_id=test_user.id, status="completed", file_path="/tmp/test.mp3")
    db_session.add(download)

    await db_session.commit()
    return artist, album, track


@pytest.mark.asyncio
async def test_get_artists(client: AsyncClient, test_user: User, sample_data):
    response = await client.get("/rest/getArtists.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "artists" in data["subsonic-response"]
    indices = data["subsonic-response"]["artists"]["index"]
    assert len(indices) > 0
    assert indices[0]["artist"][0]["name"] == "Test Artist"


@pytest.mark.asyncio
async def test_get_artist(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get(f"/rest/getArtist.view?id={artist.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert data["subsonic-response"]["artist"]["name"] == "Test Artist"
    assert len(data["subsonic-response"]["artist"]["album"]) > 0


@pytest.mark.asyncio
async def test_get_album(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get(f"/rest/getAlbum.view?id={album.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert data["subsonic-response"]["album"]["name"] == "Test Album"
    assert len(data["subsonic-response"]["album"]["song"]) > 0
    assert data["subsonic-response"]["album"]["song"][0]["title"] == "Test Song"
