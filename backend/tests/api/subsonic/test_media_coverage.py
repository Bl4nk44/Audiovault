import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.subsonic.handlers.media import parse_range_header, safe_content_disposition
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}


def test_safe_content_disposition():
    # ASCII
    assert 'inline; filename="test.mp3"' in safe_content_disposition("test.mp3")
    # Unicode
    res = safe_content_disposition("zażółć.mp3", "attachment")
    assert "attachment;" in res
    assert "filename*=UTF-8''za%C5%BC%C3%B3%C5%82%C4%87.mp3" in res
    # Empty resulting ascii
    assert 'filename="  "' in safe_content_disposition(" żółć ")


def test_parse_range_header():
    assert parse_range_header(None, 1000) == (0, 999)
    assert parse_range_header("bytes=0-499", 1000) == (0, 499)
    assert parse_range_header("bytes=500-", 1000) == (500, 999)
    assert parse_range_header("bytes=-200", 1000) == (800, 999)
    assert parse_range_header("invalid", 1000) == (0, 999)


@pytest.mark.asyncio
async def test_subsonic_stream_errors(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # Invalid ID
    params = {**subsonic_auth_params, "id": "invalid-uuid"}
    response = await client.get("/rest/stream.view", params=params)
    assert response.status_code == 200  # Subsonic returns 200 with error XML/JSON
    assert "10" in response.text  # Error code 10: Invalid ID

    # Not found in DB
    random_id = str(uuid.uuid4())
    params["id"] = random_id
    response = await client.get("/rest/stream.view", params=params)
    assert "70" in response.text  # Error code 70: Song not found

    # Found in DB but file missing on disk
    track = Track(id=uuid.uuid4(), title="Missing File", artist="Artist")
    db_session.add(track)
    await db_session.flush()
    dl = Download(
        id=uuid.uuid4(), user_id=admin_user.id, track_id=track.id, status="completed", file_path="/no/file.mp3"
    )
    db_session.add(dl)
    await db_session.commit()

    params["id"] = str(track.id)
    with patch("os.path.exists", return_value=False):
        response = await client.get("/rest/stream.view", params=params)
        assert "70" in response.text
        assert "File not found" in response.text


@pytest.mark.asyncio
async def test_subsonic_get_cover_art_fallbacks(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    track_id = uuid.uuid4()
    # Case: No remote image, file exists but no cover.jpg and no embedded art
    track = Track(id=track_id, title="No Art", artist="Artist", metadata_content={})
    db_session.add(track)
    await db_session.flush()
    dl = Download(
        id=uuid.uuid4(), user_id=admin_user.id, track_id=track.id, status="completed", file_path="/tmp/music.mp3"
    )
    db_session.add(dl)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": f"tr-{track_id}"}

    with (
        patch("os.path.exists", side_effect=lambda p: p == "/tmp/music.mp3"),  # only the mp3 exists
        patch("app.api.subsonic.handlers.media._extract_embedded_art", return_value=None),
    ):
        response = await client.get("/rest/getCoverArt.view", params=params)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_subsonic_hls_not_supported(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": str(uuid.uuid4())}
    response = await client.get("/rest/hls.view", params=params)
    assert response.status_code == 200
    assert "HLS streaming not supported" in response.text


@pytest.mark.asyncio
async def test_get_remote_image_logic():
    from app.api.subsonic.handlers.media import _get_remote_image

    url = "https://i.scdn.co/image/test"

    with patch("os.path.exists", return_value=True), patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_file.read.return_value = b"GIF89a..."  # Fake GIF
        mock_open.return_value = mock_file

        # Test cache hit
        resp = await _get_remote_image(url)
        assert resp is not None
        assert resp.headers["X-Cache"] == "HIT"
        assert resp.media_type == "image/gif"
