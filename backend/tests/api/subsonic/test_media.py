import pytest
import uuid
import os
import io
from httpx import AsyncClient
from app.models.track import Track
from app.models.download import Download
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Response

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
async def sample_media(db_session, admin_user):
    # We will mock file operations, so no physical file is needed
    file_path = "C:\\fake\\music\\test.mp3"
    
    track = Track(id=uuid.uuid4(), title="Stream Track", artist="Stream Artist")
    db_session.add(track)
    await db_session.flush()
    
    download = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path=file_path
    )
    db_session.add(download)
    await db_session.commit()
    
    return track, download

@pytest.mark.asyncio
async def test_subsonic_stream(client: AsyncClient, subsonic_auth_params, sample_media):
    track, download = sample_media
    params = {**subsonic_auth_params, "id": str(track.id)}
    
    # Mock file system and aiofiles
    with patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1024), \
         patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        
        # Configure aiofiles mock
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_file.read.return_value = b"fake audio content"
        mock_open.return_value = mock_file
        
        response = await client.get("/rest/stream.view", params=params)
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"

@pytest.mark.asyncio
async def test_subsonic_stream_range(client: AsyncClient, subsonic_auth_params, sample_media):
    track, download = sample_media
    params = {**subsonic_auth_params, "id": str(track.id)}
    headers = {"Range": "bytes=0-99"}
    
    with patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1024), \
         patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_file.read.return_value = b"A" * 100
        mock_open.return_value = mock_file
        
        response = await client.get("/rest/stream.view", params=params, headers=headers)
        assert response.status_code == 206
        assert response.headers["content-range"] == "bytes 0-99/1024"
        assert len(await response.aread()) == 100

@pytest.mark.asyncio
async def test_subsonic_download(client: AsyncClient, subsonic_auth_params, sample_media):
    track, _ = sample_media
    params = {**subsonic_auth_params, "id": str(track.id)}
    
    with patch("os.path.exists", return_value=True), \
         patch("app.api.subsonic.handlers.media.FileResponse") as mock_file_resp:
        
        mock_file_resp.return_value = Response(content=b"file content")
        
        response = await client.get("/rest/download.view", params=params)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_subsonic_get_cover_art_local(client: AsyncClient, subsonic_auth_params, sample_media):
    track, _ = sample_media
    params = {**subsonic_auth_params, "id": f"tr-{track.id}"}
    
    with patch("os.path.exists", side_effect=lambda p: "cover.jpg" in p or "test.mp3" in p), \
         patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_file.read.return_value = b"fake jpeg"
        mock_open.return_value = mock_file
        
        response = await client.get("/rest/getCoverArt.view", params=params)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

@pytest.mark.asyncio
async def test_subsonic_get_cover_art_remote(client: AsyncClient, subsonic_auth_params, db_session):
    track = Track(id=uuid.uuid4(), title="Remote Art", metadata_content={"image_url": "https://i.scdn.co/image/test"})
    db_session.add(track)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": f"tr-{track.id}"}
    
    with patch("os.path.exists", return_value=False), \
         patch("app.api.subsonic.handlers.media._get_remote_image") as mock_remote:
        mock_remote.return_value = Response(content=b"remote content", media_type="image/jpeg", headers={"X-Cache": "MISS"})
        
        response = await client.get("/rest/getCoverArt.view", params=params)
        assert response.status_code == 200
        assert response.content == b"remote content"

@pytest.mark.asyncio
async def test_subsonic_get_cover_art_remote_async(client: AsyncClient, subsonic_auth_params, db_session):
    track = Track(id=uuid.uuid4(), title="Remote Art 2", metadata_content={"image_url": "https://i.scdn.co/image/test2"})
    db_session.add(track)
    await db_session.commit()
    
    params = {**subsonic_auth_params, "id": f"tr-{track.id}"}
    
    from fastapi import Response
    mock_resp = Response(content=b"remote content", media_type="image/jpeg")
    
    with patch("os.path.exists", return_value=False), \
         patch("app.api.subsonic.handlers.media._get_remote_image", new_callable=AsyncMock) as mock_remote:
        mock_remote.return_value = mock_resp
        response = await client.get("/rest/getCoverArt.view", params=params)
        assert response.status_code == 200
        assert response.content == b"remote content"
