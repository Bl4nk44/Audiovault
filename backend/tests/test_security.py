import pytest
from pydantic import ValidationError
from app.api.v1.import_routes import ImportRequest


def test_valid_import_urls():
    valid_urls = [
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        "https://listen.tidal.com/album/12345",
        "https://music.apple.com/us/album/some-album/12345",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://soundcloud.com/user/track",
        "https://music.amazon.com/albums/B000",
    ]
    for url in valid_urls:
        req = ImportRequest(url=url)
        assert req.url == url


def test_invalid_import_urls():
    invalid_urls = [
        "https://google.com",
        "https://evil.com/spotify.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://example.com",
        "ftp://spotify.com",
    ]
    for url in invalid_urls:
        with pytest.raises(ValidationError):
            ImportRequest(url=url)
