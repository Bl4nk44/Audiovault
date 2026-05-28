import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        username="testuser", email="test@example.com", hashed_password=get_password_hash("testpass"), is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_data(db_session: AsyncSession, test_user: User):
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(title="Test Song", artist_id=artist.id, album_id=album.id, metadata_content={"genre": "Test Genre"})
    db_session.add(track)
    await db_session.flush()

    # Add Download
    download = Download(track_id=track.id, user_id=test_user.id, status="completed", file_path="/test_audio/test.mp3")
    db_session.add(download)

    await db_session.commit()
    return artist, album, track


@pytest.mark.asyncio
async def test_search2(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get("/rest/search2.view?query=Test&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "searchResult2" in data["subsonic-response"]
    results = data["subsonic-response"]["searchResult2"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["title"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))


@pytest.mark.asyncio
async def test_search3(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get("/rest/search3.view?query=Test&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "searchResult3" in data["subsonic-response"]
    results = data["subsonic-response"]["searchResult3"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["name"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))
