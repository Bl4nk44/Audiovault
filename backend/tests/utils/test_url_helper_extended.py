"""Extended tests covering resolve_redirects and DNS failure paths."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.url_helper import SSRFValidationError, extract_domain, resolve_redirects, validate_url


def test_extract_domain_no_subdomain():
    """Single-part hostname (e.g. 'localhost') returns as-is."""
    result = extract_domain("http://localhost/path")
    assert result == "localhost"


@pytest.mark.asyncio
async def test_validate_url_dns_failure():
    """DNS resolution failure returns (False, error)."""
    with patch("app.utils.url_helper.socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
        is_valid, error = validate_url("https://open.spotify.com/track/abc")
    assert is_valid is False
    assert "DNS resolution failed" in error


@pytest.mark.asyncio
async def test_validate_url_private_ip_blocked():
    """When DNS resolves to a private IP, URL should be blocked."""
    with patch(
        "app.utils.url_helper.socket.getaddrinfo", return_value=[(None, None, None, None, ("192.168.1.1", 443))]
    ):
        is_valid, error = validate_url("https://open.spotify.com/track/abc")
    assert is_valid is False
    assert "Private IP" in error


# ─── resolve_redirects ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_redirects_ssrf_blocked_on_initial_url():
    """If the initial URL fails SSRF validation, raises SSRFValidationError."""
    with pytest.raises(SSRFValidationError):
        await resolve_redirects("ftp://evil.com/attack")


@pytest.mark.asyncio
async def test_resolve_redirects_success_via_head():
    """HEAD request with redirect → returns final URL after following redirect."""
    mock_redirect = MagicMock()
    mock_redirect.status = 301
    mock_redirect.headers = {"Location": "https://soundcloud.com/artist/track"}
    mock_redirect.__aenter__ = AsyncMock(return_value=mock_redirect)
    mock_redirect.__aexit__ = AsyncMock(return_value=False)

    mock_final = MagicMock()
    mock_final.status = 200
    mock_final.__aenter__ = AsyncMock(return_value=mock_final)
    mock_final.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.side_effect = [mock_redirect, mock_final]
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://soundcloud.com/artist/track"


@pytest.mark.asyncio
async def test_resolve_redirects_redirect_to_blocked_url():
    """If HEAD redirect points to a blocked URL, raises SSRFValidationError before request."""
    mock_response = MagicMock()
    mock_response.status = 301
    mock_response.headers = {"Location": "https://blocked-host.example/evil"}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def fake_validate(url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return True, ""  # initial URL passes
        return False, "Private IP blocked"  # redirect destination blocked

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        with pytest.raises(SSRFValidationError, match="Redirect blocked"):
            await resolve_redirects("https://on.soundcloud.com/abc")


@pytest.mark.asyncio
async def test_resolve_redirects_head_fails_falls_back_to_get():
    """When HEAD raises (e.g. 405), falls back to GET on the same session."""
    mock_redirect = MagicMock()
    mock_redirect.status = 301
    mock_redirect.headers = {"Location": "https://soundcloud.com/artist/track"}
    mock_redirect.__aenter__ = AsyncMock(return_value=mock_redirect)
    mock_redirect.__aexit__ = AsyncMock(return_value=False)

    mock_final = MagicMock()
    mock_final.status = 200
    mock_final.__aenter__ = AsyncMock(return_value=mock_final)
    mock_final.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.side_effect = Exception("405 Method Not Allowed")
    mock_session.get.side_effect = [mock_redirect, mock_final]
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://soundcloud.com/artist/track"


@pytest.mark.asyncio
async def test_resolve_redirects_get_also_fails_returns_original():
    """When both HEAD and GET fail, returns the original URL."""
    mock_session = MagicMock()
    mock_session.head.side_effect = Exception("HEAD failed")
    mock_session.get.side_effect = Exception("GET also failed")
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    original = "https://on.soundcloud.com/abc"

    def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects(original)

    assert result == original


@pytest.mark.asyncio
async def test_resolve_redirects_empty_location_header():
    """Redirect status with no Location header → returns current URL."""
    mock_response = MagicMock()
    mock_response.status = 302
    mock_response.headers = {}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=lambda u: (True, "")),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://on.soundcloud.com/abc"


@pytest.mark.asyncio
async def test_resolve_redirects_relative_location():
    """Relative redirect Location is resolved against the current URL."""
    mock_redirect = MagicMock()
    mock_redirect.status = 302
    mock_redirect.headers = {"Location": "/artist/track"}
    mock_redirect.__aenter__ = AsyncMock(return_value=mock_redirect)
    mock_redirect.__aexit__ = AsyncMock(return_value=False)

    mock_final = MagicMock()
    mock_final.status = 200
    mock_final.__aenter__ = AsyncMock(return_value=mock_final)
    mock_final.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.side_effect = [mock_redirect, mock_final]
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=lambda u: (True, "")),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://on.soundcloud.com/artist/track"


@pytest.mark.asyncio
async def test_resolve_redirects_max_hops_exhausted():
    """Infinite redirect loop stops after _MAX_REDIRECTS and returns last URL."""
    mock_redirect = MagicMock()
    mock_redirect.status = 301
    mock_redirect.headers = {"Location": "https://soundcloud.com/loop"}
    mock_redirect.__aenter__ = AsyncMock(return_value=mock_redirect)
    mock_redirect.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.return_value = mock_redirect
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=lambda u: (True, "")),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://soundcloud.com/loop"


@pytest.mark.asyncio
async def test_resolve_redirects_get_redirect_to_blocked():
    """GET fallback redirect to blocked URL raises SSRFValidationError before request."""
    mock_get_response = MagicMock()
    mock_get_response.status = 301
    mock_get_response.headers = {"Location": "https://blocked-host.example/evil"}
    mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
    mock_get_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.side_effect = Exception("HEAD failed")
    mock_session.get.return_value = mock_get_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def fake_validate(url):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return True, ""
        return False, "Private IP blocked"

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        with pytest.raises(SSRFValidationError):
            await resolve_redirects("https://on.soundcloud.com/abc")
