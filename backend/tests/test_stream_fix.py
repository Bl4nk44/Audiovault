from unittest.mock import patch

import pytest

from app.api.v1.stream import _extract_direct_url


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
