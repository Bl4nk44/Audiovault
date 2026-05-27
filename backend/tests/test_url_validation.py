"""
Tests for SSRF protection in url_helper module.
"""

import pytest

from app.utils.url_helper import (
    is_allowed_domain,
    is_private_ip,
    validate_url,
)


class TestIsPrivateIP:
    """Tests for is_private_ip function."""

    def test_loopback_ipv4(self):
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.255.255.255") is True

    def test_private_class_a(self):
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True

    def test_private_class_b(self):
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True

    def test_private_class_c(self):
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True

    def test_link_local(self):
        assert is_private_ip("169.254.0.1") is True

    def test_loopback_ipv6(self):
        assert is_private_ip("::1") is True

    def test_public_ip(self):
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("142.250.185.238") is False  # Google

    def test_invalid_ip(self):
        assert is_private_ip("not-an-ip") is False
        assert is_private_ip("") is False


class TestIsAllowedDomain:
    """Tests for is_allowed_domain function."""

    def test_spotify_domains(self):
        assert is_allowed_domain("https://open.spotify.com/track/123") is True
        assert is_allowed_domain("https://spotify.link/abc") is True
        assert is_allowed_domain("https://api.spotify.com/v1/tracks") is True

    def test_youtube_domains(self):
        assert is_allowed_domain("https://www.youtube.com/watch?v=123") is True
        assert is_allowed_domain("https://youtu.be/xyz") is True
        assert is_allowed_domain("https://music.youtube.com/watch?v=123") is True

    def test_deezer_domains(self):
        assert is_allowed_domain("https://deezer.com/track/123") is True
        assert is_allowed_domain("https://deezer.page.link/abc") is True

    def test_apple_music_domains(self):
        assert is_allowed_domain("https://music.apple.com/album/123") is True
        assert is_allowed_domain("https://itunes.apple.com/song/456") is True

    def test_soundcloud_domains(self):
        assert is_allowed_domain("https://soundcloud.com/artist/track") is True
        assert is_allowed_domain("https://on.soundcloud.com/xyz") is True

    def test_tidal_domains(self):
        assert is_allowed_domain("https://tidal.com/browse/track/123") is True
        assert is_allowed_domain("https://listen.tidal.com/track/123") is True

    def test_amazon_domains(self):
        assert is_allowed_domain("https://music.amazon.com/albums/B123") is True
        assert is_allowed_domain("https://amzn.to/abc") is True

    def test_blocked_domains(self):
        assert is_allowed_domain("https://evil.com/malware") is False
        assert is_allowed_domain("https://localhost/api") is False
        assert is_allowed_domain("https://internal.company.com/secrets") is False
        assert is_allowed_domain("http://192.168.1.1/admin") is False


class TestValidateUrl:
    """Tests for validate_url async function."""

    @pytest.mark.asyncio
    async def test_valid_spotify_url(self):
        is_valid, error = validate_url("https://open.spotify.com/track/123")
        assert is_valid is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_invalid_scheme(self):
        is_valid, error = validate_url("ftp://spotify.com/file")
        assert is_valid is False
        assert "Invalid URL scheme" in error

    @pytest.mark.asyncio
    async def test_blocked_domain(self):
        is_valid, error = validate_url("https://evil-site.com/malware")
        assert is_valid is False
        assert "Domain not allowed" in error

    @pytest.mark.asyncio
    async def test_no_hostname(self):
        is_valid, error = validate_url("https:///path/only")
        assert is_valid is False
        assert "No hostname" in error

    @pytest.mark.asyncio
    async def test_javascript_scheme(self):
        is_valid, error = validate_url("javascript:alert(1)")
        assert is_valid is False
        assert "Invalid URL scheme" in error

    @pytest.mark.asyncio
    async def test_data_scheme(self):
        is_valid, error = validate_url("data:text/html,<script>alert(1)</script>")
        assert is_valid is False
        assert "Invalid URL scheme" in error
