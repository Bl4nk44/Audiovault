"""Tests for iOS-compatible stream format selection and streaming response.

iOS Safari cannot decode opus/webm audio, while desktop Chrome can — the
previous yt-dlp format ("bestaudio/best") usually picked webm/opus on
YouTube, so search results played on desktop but not on iPhone. These tests
cover the AAC/m4a format preference and the switch from a fully-buffered
Response to a StreamingResponse with an accurate Content-Type.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.stream import _build_ydl_format, _extract_direct_url

STREAM_URL_CACHE_KEY = "stream_url:abc"


def test_build_ydl_format_prefers_m4a_then_mp4a_then_any():
    fmt = _build_ydl_format()
    parts = fmt.split("/")
    assert parts[0] == "bestaudio[ext=m4a]"
    assert parts[-1] == "bestaudio"


@pytest.mark.asyncio
async def test_extract_direct_url_media_type_for_m4a():
    with patch("app.api.v1.stream.yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value
        instance.__enter__.return_value = instance
        instance.extract_info.return_value = {
            "url": "https://manifest.googlevideo.com/m4a",
            "ext": "m4a",
            "http_headers": {},
        }
        url, headers, media_type = await _extract_direct_url("https://www.youtube.com/watch?v=test")

    assert url == "https://manifest.googlevideo.com/m4a"
    assert headers == {}
    assert media_type == "audio/mp4"


@pytest.mark.asyncio
async def test_extract_direct_url_media_type_for_webm():
    with patch("app.api.v1.stream.yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value
        instance.__enter__.return_value = instance
        instance.extract_info.return_value = {
            "url": "https://manifest.googlevideo.com/webm",
            "ext": "webm",
            "http_headers": {},
        }
        url, headers, media_type = await _extract_direct_url("https://www.youtube.com/watch?v=test")

    assert url == "https://manifest.googlevideo.com/webm"
    assert media_type == "audio/webm"


@pytest.mark.asyncio
async def test_extract_direct_url_defaults_to_mp4_when_ext_missing():
    """No 'ext' key from yt-dlp -> conservative default, not a lie like audio/mpeg."""
    with patch("app.api.v1.stream.yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value
        instance.__enter__.return_value = instance
        instance.extract_info.return_value = {
            "url": "https://manifest.googlevideo.com/unknown",
            "http_headers": {},
        }
        _url, _headers, media_type = await _extract_direct_url("https://www.youtube.com/watch?v=test")

    assert media_type == "audio/mp4"


@pytest.mark.asyncio
async def test_extract_direct_url_uses_m4a_preferring_format():
    """The ydl_opts format string passed to yt-dlp must prefer m4a."""
    captured: dict = {}

    def fake_ytdl(opts):
        captured.update(opts)
        instance = MagicMock()
        instance.__enter__.return_value = instance
        instance.extract_info.return_value = {"url": "http://x", "ext": "m4a", "http_headers": {}}
        return instance

    with patch("app.api.v1.stream.yt_dlp.YoutubeDL", side_effect=fake_ytdl):
        await _extract_direct_url("https://www.youtube.com/watch?v=test")

    assert captured["format"] == _build_ydl_format()
    assert captured["format"].startswith("bestaudio[ext=m4a]")


@pytest.mark.asyncio
async def test_stream_track_streams_and_reports_real_media_type(client: AsyncClient):
    """Endpoint returns the real upstream media type (not the hardcoded audio/mpeg lie)
    and passes through a 206 Partial Content status for Range requests."""
    with (
        patch("app.api.v1.stream._resolve_stream_url", new_callable=AsyncMock) as m_resolve,
        patch("app.api.v1.stream._extract_direct_url", new_callable=AsyncMock) as m_extract,
    ):
        m_resolve.return_value = "https://youtube.com/watch?v=abc"
        m_extract.return_value = ("https://googlevideo.com/direct-audio-url", {}, "audio/webm")

        with patch("httpx.AsyncClient") as mock_client_cls:

            async def fake_aiter_bytes(chunk_size=None):
                yield b"chunk-1"
                yield b"chunk-2"

            mock_upstream = MagicMock()
            mock_upstream.status_code = 206
            mock_upstream.headers = {"content-range": "bytes 0-1/2", "content-length": "14"}
            mock_upstream.aiter_bytes = fake_aiter_bytes
            mock_upstream.aclose = AsyncMock()

            mock_client_instance = MagicMock()
            mock_client_instance.build_request = MagicMock(return_value=MagicMock())
            mock_client_instance.send = AsyncMock(return_value=mock_upstream)
            mock_client_instance.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client_instance

            response = await client.get(
                "/api/v1/stream/abc.mp3",
                headers={"Range": "bytes=0-1"},
                follow_redirects=False,
            )

    assert response.status_code == 206
    assert response.headers["Content-Type"] == "audio/webm"
    assert response.content == b"chunk-1chunk-2"
    assert response.headers["Content-Range"] == "bytes 0-1/2"
    assert response.headers["Accept-Ranges"] == "bytes"
    mock_upstream.aclose.assert_awaited_once()
    mock_client_instance.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_track_upstream_403_returns_502_and_invalidates_cache(client: AsyncClient):
    """An expired googlevideo URL (cache TTL outlives the token) answers with an
    upstream 403/HTML body. We must not stream that as if it were audio — return
    502, close both httpx handles, and drop the stale cached URL so the next
    request re-resolves instead of hitting the same dead link."""
    with (
        patch("app.api.v1.stream._resolve_stream_url", new_callable=AsyncMock) as m_resolve,
        patch("app.api.v1.stream._extract_direct_url", new_callable=AsyncMock) as m_extract,
        patch("app.api.v1.stream.cache_manager.delete", new_callable=AsyncMock) as m_delete,
    ):
        m_resolve.return_value = "https://youtube.com/watch?v=abc"
        m_extract.return_value = ("https://googlevideo.com/expired-audio-url", {}, "audio/mp4")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_upstream = MagicMock()
            mock_upstream.status_code = 403
            mock_upstream.headers = {}
            mock_upstream.aclose = AsyncMock()

            mock_client_instance = MagicMock()
            mock_client_instance.build_request = MagicMock(return_value=MagicMock())
            mock_client_instance.send = AsyncMock(return_value=mock_upstream)
            mock_client_instance.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client_instance

            response = await client.get("/api/v1/stream/abc.mp3", follow_redirects=False)

    assert response.status_code == 502
    mock_upstream.aclose.assert_awaited_once()
    mock_client_instance.aclose.assert_awaited_once()
    m_delete.assert_awaited_once_with(STREAM_URL_CACHE_KEY)


@pytest.mark.asyncio
async def test_stream_track_no_accept_ranges_when_upstream_lacks_support(client: AsyncClient):
    """A plain 200 upstream response with no accept-ranges header must not
    advertise range support to the browser — that was previously hardcoded."""
    with (
        patch("app.api.v1.stream._resolve_stream_url", new_callable=AsyncMock) as m_resolve,
        patch("app.api.v1.stream._extract_direct_url", new_callable=AsyncMock) as m_extract,
    ):
        m_resolve.return_value = "https://youtube.com/watch?v=abc"
        m_extract.return_value = ("https://googlevideo.com/direct-audio-url", {}, "audio/mp4")

        with patch("httpx.AsyncClient") as mock_client_cls:

            async def fake_aiter_bytes(chunk_size=None):
                yield b"full-body"

            mock_upstream = MagicMock()
            mock_upstream.status_code = 200
            mock_upstream.headers = {"content-length": "9"}
            mock_upstream.aiter_bytes = fake_aiter_bytes
            mock_upstream.aclose = AsyncMock()

            mock_client_instance = MagicMock()
            mock_client_instance.build_request = MagicMock(return_value=MagicMock())
            mock_client_instance.send = AsyncMock(return_value=mock_upstream)
            mock_client_instance.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client_instance

            response = await client.get("/api/v1/stream/abc.mp3", follow_redirects=False)

    assert response.status_code == 200
    assert "Accept-Ranges" not in response.headers
