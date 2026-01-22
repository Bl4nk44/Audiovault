import pytest
import uuid
import os
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.track import Track
from app.models.download import Download
from app.models.album import Album
from app.api.v1 import stream
from fastapi import Response

@pytest.mark.asyncio
async def test_get_track_cover_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/stream/{uuid.uuid4()}/cover")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_track_cover_success(client: AsyncClient, db_session):
    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Stream Track", artist="Stream Artist")
    db_session.add(track)
    await db_session.commit()
    
    download_id = uuid.uuid4()
    download = Download(id=download_id, track_id=track_id, file_path="/tmp/fake.mp3", status="completed")
    db_session.add(download)
    await db_session.commit()
    
    with (
        patch("os.path.exists", return_value=True),
        patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock) as m_resolve
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
        patch("app.api.v1.stream._stream_content") as m_stream
    ):
        m_resolve.return_value = "https://youtube.com/watch?v=123"
        m_extract.return_value = ("https://googlevideo.com/...", {"User-Agent": "test"})
        m_stream.return_value = [b"chunk1", b"chunk2"]
        
        response = await client.get("/api/v1/stream/123.mp3")
        assert response.status_code == 200
        assert response.content == b"chunk1chunk2"

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
    from mutagen.id3 import ID3, APIC
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
    with patch("os.path.exists", return_value=True), \
         patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        
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
    album = Album(id=uuid.uuid4(), title="Test Album", images={"url": "https://example.com/cover.jpg"})
    db_session.add(album)
    await db_session.commit()
    
    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"remote_cover_data"
        mock_response.headers = {"Content-Type": "image/jpeg"}
        
        # Correctly mock aiohttp context manager
        mock_get.return_value.__aenter__.return_value = mock_response
        
        response = await client.get(f"/api/v1/stream/album/{album.id}/cover")
        assert response.status_code in [200, 307]
@pytest.mark.asyncio
async def test_get_track_cover_embedded_fallback(client: AsyncClient, db_session):
    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Embedded Track", artist="Artist")
    db_session.add(track)
    
    download = Download(id=uuid.uuid4(), track_id=track_id, file_path="/tmp/embedded.mp3", status="completed")
    db_session.add(download)
    await db_session.commit()
    
    with (
        patch("os.path.exists", side_effect=lambda p: p == "/tmp/embedded.mp3"),
        patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock, return_value=(None, None)),
        patch("app.api.v1.stream._extract_embedded_cover_art", new_callable=AsyncMock) as m_embed
    ):
        m_embed.return_value = (b"embedded_data", "image/png")
        response = await client.get(f"/api/v1/stream/{track_id}/cover")
        assert response.status_code == 200
        assert response.content == b"embedded_data"

@pytest.mark.asyncio
async def test_get_track_cover_album_fallback(client: AsyncClient, db_session):
    album_id = uuid.uuid4()
    album = Album(id=album_id, title="Test Album", images={"300": "http://example.com/300.jpg"})
    db_session.add(album)
    
    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Album Fallback Track", artist="Artist", album_id=album_id)
    db_session.add(track)
    await db_session.commit()
    
    # Mock no file_path to trigger album fallback
    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock, return_value=(track, None)):
        response = await client.get(f"/api/v1/stream/{track_id}/cover")
        assert response.status_code == 307
        assert response.headers["location"] == "http://example.com/300.jpg"

@pytest.mark.asyncio
async def test_resolve_stream_url_cached(client: AsyncClient):
    with patch("app.api.v1.stream.cache_manager.get", new_callable=AsyncMock) as m_cache:
        m_cache.return_value = "https://cached-url.com"
        url = await stream._resolve_stream_url("some_id")
        assert url == "https://cached-url.com"
        assert m_cache.called

@pytest.mark.asyncio
async def test_resolve_stream_url_spotify_to_youtube(client: AsyncClient):
    with (
        patch("app.api.v1.stream.cache_manager.get", new_callable=AsyncMock, return_value=None),
        patch("app.api.v1.stream._get_spotify_track_sync") as m_spot,
        patch("app.api.v1.stream._resolve_stream_url_sync") as m_yt,
        patch("app.api.v1.stream.cache_manager.set", new_callable=AsyncMock) as m_set
    ):
        m_spot.return_value = {"title": "S", "artist": "A"}
        m_yt.return_value = "https://youtube.com/watch?v=spot"
        
        url = await stream._resolve_stream_url("spotify_id")
        assert url == "https://youtube.com/watch?v=spot"
        assert m_set.called
