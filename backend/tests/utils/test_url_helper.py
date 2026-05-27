import pytest

from app.utils.url_helper import (
    extract_domain,
    is_allowed_domain,
    is_private_ip,
    validate_url,
)


def test_is_private_ip_loopback():
    assert is_private_ip("127.0.0.1") is True


def test_is_private_ip_private_class_a():
    assert is_private_ip("10.0.0.1") is True


def test_is_private_ip_private_class_b():
    assert is_private_ip("172.16.0.1") is True


def test_is_private_ip_private_class_c():
    assert is_private_ip("192.168.1.1") is True


def test_is_private_ip_public():
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("142.250.185.78") is False


def test_is_private_ip_invalid():
    assert is_private_ip("not-an-ip") is False


def test_extract_domain_spotify():
    assert extract_domain("https://open.spotify.com/track/abc") == "spotify.com"


def test_extract_domain_youtube():
    assert extract_domain("https://www.youtube.com/watch?v=123") == "youtube.com"


def test_extract_domain_short():
    assert extract_domain("https://youtu.be/123") == "youtu.be"


def test_is_allowed_domain_spotify():
    assert is_allowed_domain("https://open.spotify.com/track/abc") is True


def test_is_allowed_domain_youtube():
    assert is_allowed_domain("https://www.youtube.com/watch?v=123") is True


def test_is_allowed_domain_music_youtube():
    assert is_allowed_domain("https://music.youtube.com/watch?v=123") is True


def test_is_allowed_domain_deezer():
    assert is_allowed_domain("https://www.deezer.com/track/123") is True


def test_is_allowed_domain_blocked():
    assert is_allowed_domain("https://evil.com/malware") is False
    assert is_allowed_domain("https://localhost/api") is False


@pytest.mark.asyncio
async def test_validate_url_valid():
    is_valid, error = validate_url("https://open.spotify.com/track/abc")
    assert is_valid is True
    assert error == ""


@pytest.mark.asyncio
async def test_validate_url_invalid_scheme():
    is_valid, error = validate_url("ftp://open.spotify.com/track/abc")
    assert is_valid is False
    assert "Invalid URL scheme" in error


@pytest.mark.asyncio
async def test_validate_url_no_hostname():
    is_valid, error = validate_url("https:///path")
    assert is_valid is False
    assert "No hostname" in error


@pytest.mark.asyncio
async def test_validate_url_blocked_domain():
    is_valid, error = validate_url("https://evil.com/malware")
    assert is_valid is False
    assert "not allowed" in error
