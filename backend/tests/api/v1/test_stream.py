import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.v1 import stream
from app.models.album import Album
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_track_cover_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/stream/{uuid.uuid4()}/cover")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_track_cover_success(client: AsyncClient, db_session):
    user = User(id=uuid.uuid4(), email="test@example.com", username="testuser", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Stream Track", artist="Stream Artist")
    db_session.add(track)
    await db_session.commit()

    download_id = uuid.uuid4()
    download = Download(
        id=download_id,
        track_id=track_id,
        user_id=user.id,
        file_path="/tmp/fake.mp3",
        status="completed",
    )
    db_session.add(download)
    await db_session.commit()

    with (
        patch("os.path.exists", return_value=True),
        patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock) as m_resolve,
    ):
        m_resolve.return_value = (b"fake_image_data", "image/jpeg")
        response = await client.get(f"/api/v1/stream/{track_id}/cover")
        assert response.status_code == 200
        assert response.content == b"fake_image_data"


@pytest.mark.asyncio
async def test_stream_track_success(client: AsyncClient):
    with (
        patch("app.api.v1.stream._resolve_stream_url", new_callable=AsyncMock) as m_resolve,
        patch("app.api.v1.stream._extract_direct_url", new_callable=AsyncMock) as m_extract,
    ):
        m_resolve.return_value = "https://youtube.com/watch?v=123"
        m_extract.return_value = ("https://googlevideo.com/direct-audio-url", {"User-Agent": "test"})

        # Mock httpx to avoid external call and return fake audio
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_upstream = AsyncMock()
            mock_upstream.status_code = 200
            mock_upstream.headers = {"Content-Type": "audio/mpeg", "Content-Length": "123"}
            mock_upstream.content = b"fake_audio_content"

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_upstream
            mock_client_cls.return_value = mock_client_instance

            response = await client.get("/api/v1/stream/123.mp3", follow_redirects=False)

            assert response.status_code == 200
            assert response.content == b"fake_audio_content"
            assert response.headers["Content-Type"] == "audio/mpeg"


def test_extract_art_flac_with_pictures():
    mock_audio = MagicMock()
    mock_picture = MagicMock()
    mock_picture.data = b"flac_picture_data"
    mock_picture.mime = "image/jpeg"
    mock_audio.pictures = [mock_picture]

    data, mime = stream._extract_art_flac(mock_audio)
    assert data == b"flac_picture_data"
    assert mime == "image/jpeg"


def test_extract_art_flac_no_pictures():
    mock_audio = MagicMock()
    mock_audio.pictures = []

    data, mime = stream._extract_art_flac(mock_audio)
    assert data is None
    assert mime is None


def test_extract_art_id3_with_apic():
    from mutagen.id3 import APIC, ID3

    mock_audio = MagicMock()
    mock_apic = MagicMock(spec=APIC)
    mock_apic.data = b"id3_apic_data"
    mock_apic.mime = "image/png"
    mock_tags = MagicMock(spec=ID3)
    mock_tags.values.return_value = [mock_apic]
    mock_audio.tags = mock_tags

    data, mime = stream._extract_art_id3(mock_audio)
    assert data == b"id3_apic_data"
    assert mime == "image/png"


def test_extract_art_mp4_with_cover():
    import mutagen.mp4

    mock_audio = MagicMock()
    mock_cover = MagicMock(spec=mutagen.mp4.MP4Cover)
    mock_cover.__bytes__ = lambda self: b"mp4_cover_data"
    mock_cover.imageformat = mutagen.mp4.MP4Cover.FORMAT_JPEG
    mock_audio.tags = {"covr": [mock_cover]}

    data, mime = stream._extract_art_mp4(mock_audio)
    assert data is not None
    assert mime == "image/jpeg"


def test_extract_art_sync_returns_none_on_error():
    with patch("mutagen.File", return_value=None):
        data, mime = stream._extract_art_sync("/fake/path.mp3")
        assert data is None
        assert mime is None


@pytest.mark.asyncio
async def test_resolve_local_cover_file_found():
    with patch("os.path.exists", return_value=True), patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_file.read.return_value = b"jpeg_cover_content"
        mock_open.return_value = mock_file

        data, mime = await stream._resolve_local_cover_file("/fake/path")
        assert data == b"jpeg_cover_content"
        assert mime == "image/jpeg"

    with patch("os.path.exists", return_value=False):
        result = await stream._resolve_local_cover_file("/fake/path")
        assert result == (None, None)


@pytest.mark.asyncio
async def test_get_album_cover_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/stream/album/{uuid.uuid4()}/cover")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_album_cover_success(client: AsyncClient, db_session):
    album = Album(id=uuid.uuid4(), title="Test Album", images={"300": "https://i.scdn.co/image/cover.jpg"})
    db_session.add(album)
    await db_session.commit()
    await db_session.refresh(album)

    # get_album_cover returns RedirectResponse(307) if cover exists
    response = await client.get(f"/api/v1/stream/album/{album.id}/cover", follow_redirects=False)
    assert response.status_code in [200, 307], f"Response: {response.status_code}, Text: {response.text}"
    if response.status_code == 307:
        assert response.headers["location"] == "https://i.scdn.co/image/cover.jpg"


@pytest.mark.asyncio
async def test_get_track_cover_embedded_fallback(client: AsyncClient, db_session):
    user = User(id=uuid.uuid4(), email="embed@example.com", username="embeduser", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Embedded Track", artist="Artist")
    db_session.add(track)

    download = Download(
        id=uuid.uuid4(),
        track_id=track_id,
        user_id=user.id,
        file_path="/tmp/embedded.mp3",
        status="completed",
    )
    db_session.add(download)
    await db_session.commit()

    with (
        patch("os.path.exists", side_effect=lambda p: p == "/tmp/embedded.mp3"),
        patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock, return_value=(None, None)),
        patch("app.api.v1.stream._extract_embedded_cover_art", new_callable=AsyncMock) as m_embed,
    ):
        m_embed.return_value = (b"embedded_data", "image/png")
        response = await client.get(f"/api/v1/stream/{track_id}/cover")
        assert response.status_code == 200
        assert response.content == b"embedded_data"


@pytest.mark.asyncio
async def test_get_track_cover_album_fallback(client: AsyncClient, db_session):
    album_id = uuid.uuid4()
    album = Album(id=album_id, title="Test Album", images={"300": "https://i.scdn.co/image/300.jpg"})
    db_session.add(album)

    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Album Fallback Track", artist="Artist", album_id=album_id)
    db_session.add(track)
    await db_session.commit()

    # Mock no file_path to trigger album fallback
    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock, return_value=(track, None)):
        response = await client.get(f"/api/v1/stream/{track_id}/cover")
        assert response.status_code == 307
        assert response.headers["location"] == "https://i.scdn.co/image/300.jpg"


@pytest.mark.asyncio
async def test_resolve_stream_url_cached(client: AsyncClient):
    with patch("app.api.v1.stream.cache_manager.get", new_callable=AsyncMock) as m_cache:
        m_cache.return_value = "https://cached-url.com"
        url = await stream._resolve_stream_url("some_id", AsyncMock())
        assert url == "https://cached-url.com"
        assert m_cache.called


@pytest.mark.asyncio
async def test_resolve_stream_url_db_track_to_youtube(client: AsyncClient):
    """When a track is found in DB (no youtube_id), resolve via YouTube search."""
    mock_track = MagicMock()
    mock_track.youtube_id = None
    mock_track.title = "Song"
    mock_track.artist = "Artist"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_track

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    with (
        patch("app.api.v1.stream.cache_manager.get", new_callable=AsyncMock, return_value=None),
        patch(
            "app.api.v1.stream._youtube_search_url",
            new_callable=AsyncMock,
            return_value="https://www.youtube.com/watch?v=spot",
        ),
        patch("app.api.v1.stream.cache_manager.set", new_callable=AsyncMock) as m_set,
    ):
        url = await stream._resolve_stream_url("spotify_id", mock_db)
        assert url == "https://www.youtube.com/watch?v=spot"
        assert m_set.called
