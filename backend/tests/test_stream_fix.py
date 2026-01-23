from unittest.mock import AsyncMock, patch

import pytest
from app.api.v1.stream import _extract_direct_url, _stream_content


# Mock yt_dlp to return specific headers and URL
@pytest.fixture
def mock_yt_dlp():
    with patch("app.api.v1.stream.yt_dlp.YoutubeDL") as mock:
        instance = mock.return_value
        instance.__enter__.return_value = instance

        # Setup extract_info return value
        def extract_info_side_effect(url, download=False):
            return {
                "url": "https://manifest.googlevideo.com/playback",
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": "https://www.youtube.com/",
                    "Cookie": "CONSENT=YES+cb.20210328-17-p0.en+FX+417",
                },
            }

        instance.extract_info.side_effect = extract_info_side_effect
        yield instance


@pytest.mark.asyncio
async def test_extract_direct_url_returns_headers(mock_yt_dlp):
    """
    Test that _extract_direct_url returns both url and headers.
    """
    url, headers = await _extract_direct_url("https://www.youtube.com/watch?v=test")

    assert url == "https://manifest.googlevideo.com/playback"
    assert headers is not None
    assert (
        headers["User-Agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
    assert headers["Referer"] == "https://www.youtube.com/"


@pytest.mark.asyncio
async def test_stream_content_uses_headers():
    """
    Test that _stream_content passes headers to aiohttp.
    """
    test_url = "https://example.com/stream"
    test_headers = {"User-Agent": "TestAgent"}

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session_instance = MockSession.return_value
        mock_session_instance.__aenter__.return_value = mock_session_instance

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response

        # Mock iter_chunked to return one chunk then stop
        async def iter_chunked(n):
            yield b"audio_data"

        mock_response.content.iter_chunked = iter_chunked

        # Setup get to return the mock response
        mock_session_instance.get.return_value = mock_response

        # Run the generator

        # Note: We need to adapt this call based on how we modify the function signature
        # This test assumes we WILL modify existing _stream_content to take headers

        # Using a wrapper to consume the async generator
        chunks = [chunk async for chunk in _stream_content(test_url, headers=test_headers)]
        assert len(chunks) > 0

        # Verify headers were passed to get() or Session constructor?
        # Ideally passed to get() for per-request flexibility, or ClientSession(headers=...)
        # Let's check session.get calls
        mock_session_instance.get.assert_called_with(test_url, headers=test_headers)
