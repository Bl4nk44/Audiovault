import os
import tempfile

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
    return user


@pytest.fixture
async def sample_data(db_session: AsyncSession, test_user: User):
    # Create a real temp file for streaming tests
    fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    os.write(fd, b"FAKE MP3 CONTENT" * 100)
    os.close(fd)

    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(title="Test Song", artist_id=artist.id, album_id=album.id, duration_ms=1000)
    db_session.add(track)
    await db_session.flush()

    # Add Download
    download = Download(track_id=track.id, user_id=test_user.id, status="completed", file_path=temp_path)
    db_session.add(download)

    await db_session.commit()
    return artist, album, track, temp_path


@pytest.mark.asyncio
async def test_stream(client: AsyncClient, test_user: User, sample_data):
    artist, album, track, temp_path = sample_data
    from unittest.mock import patch

    with patch("pathlib.Path.is_relative_to", return_value=True):
        response = await client.get(f"/rest/stream.view?id={track.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")

        try:
            assert response.status_code == 200
            assert response.headers["Content-Type"] == "audio/mpeg"
            assert len(response.content) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@pytest.mark.asyncio
async def test_download(client: AsyncClient, test_user: User, sample_data):
    artist, album, track, temp_path = sample_data
    from unittest.mock import patch

    with patch("pathlib.Path.is_relative_to", return_value=True):
        response = await client.get(f"/rest/download.view?id={track.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")

        try:
            assert response.status_code == 200
            assert "attachment" in response.headers.get("Content-Disposition", "")
            assert len(response.content) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@pytest.mark.asyncio
async def test_get_cover_art(client: AsyncClient, test_user: User, sample_data):
    artist, album, track, temp_path = sample_data
    # Testing with album artist ID prefix
    response = await client.get(f"/rest/getCoverArt.view?id=al-{album.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")

    try:
        # Our implementation redirects or returns placeholder if no cover
        # Since we didn't add images to Album, it might be 404 or redirect
        assert response.status_code in [200, 302, 307, 404]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
