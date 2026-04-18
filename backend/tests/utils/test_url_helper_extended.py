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
        is_valid, error = await validate_url("https://open.spotify.com/track/abc")
    assert is_valid is False
    assert "DNS resolution failed" in error


@pytest.mark.asyncio
async def test_validate_url_private_ip_blocked():
    """When DNS resolves to a private IP, URL should be blocked."""
    with patch(
        "app.utils.url_helper.socket.getaddrinfo", return_value=[(None, None, None, None, ("192.168.1.1", 443))]
    ):
        is_valid, error = await validate_url("https://open.spotify.com/track/abc")
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
    """HEAD request succeeds → returns final URL."""
    mock_response = MagicMock()
    mock_response.url = "https://soundcloud.com/artist/track"
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    async def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://soundcloud.com/artist/track"


@pytest.mark.asyncio
async def test_resolve_redirects_redirect_to_blocked_url():
    """If HEAD redirect resolves to a blocked URL, raises SSRFValidationError."""
    mock_response = MagicMock()
    mock_response.url = "https://192.168.1.1/evil"
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.head.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    async def fake_validate(url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return True, ""  # initial URL passes
        return False, "Private IP blocked"

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", return_value=mock_session),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        with pytest.raises(SSRFValidationError, match="Redirect blocked"):
            await resolve_redirects("https://on.soundcloud.com/abc")


@pytest.mark.asyncio
async def test_resolve_redirects_head_fails_falls_back_to_get():
    """When HEAD raises (e.g. 405), falls back to GET."""
    mock_get_response = MagicMock()
    mock_get_response.url = "https://soundcloud.com/artist/track"
    mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
    mock_get_response.__aexit__ = AsyncMock(return_value=False)

    mock_head_session = MagicMock()
    mock_head_session.head.side_effect = Exception("405 Method Not Allowed")
    mock_head_session.__aenter__ = AsyncMock(return_value=mock_head_session)
    mock_head_session.__aexit__ = AsyncMock(return_value=False)

    mock_get_session = MagicMock()
    mock_get_session.get.return_value = mock_get_response
    mock_get_session.__aenter__ = AsyncMock(return_value=mock_get_session)
    mock_get_session.__aexit__ = AsyncMock(return_value=False)

    sessions = [mock_head_session, mock_get_session]
    session_iter = iter(sessions)

    async def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", side_effect=lambda: next(session_iter)),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects("https://on.soundcloud.com/abc")

    assert result == "https://soundcloud.com/artist/track"


@pytest.mark.asyncio
async def test_resolve_redirects_get_also_fails_returns_original():
    """When both HEAD and GET fail, returns the original URL."""
    mock_head_session = MagicMock()
    mock_head_session.head.side_effect = Exception("HEAD failed")
    mock_head_session.__aenter__ = AsyncMock(return_value=mock_head_session)
    mock_head_session.__aexit__ = AsyncMock(return_value=False)

    mock_get_session = MagicMock()
    mock_get_session.get.side_effect = Exception("GET also failed")
    mock_get_session.__aenter__ = AsyncMock(return_value=mock_get_session)
    mock_get_session.__aexit__ = AsyncMock(return_value=False)

    sessions = [mock_head_session, mock_get_session]
    session_iter = iter(sessions)

    original = "https://on.soundcloud.com/abc"

    async def fake_validate(url):
        return True, ""

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", side_effect=lambda: next(session_iter)),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        result = await resolve_redirects(original)

    assert result == original


@pytest.mark.asyncio
async def test_resolve_redirects_get_redirect_to_blocked():
    """GET fallback that redirects to a blocked URL raises SSRFValidationError."""
    mock_head_session = MagicMock()
    mock_head_session.head.side_effect = Exception("HEAD failed")
    mock_head_session.__aenter__ = AsyncMock(return_value=mock_head_session)
    mock_head_session.__aexit__ = AsyncMock(return_value=False)

    mock_get_response = MagicMock()
    mock_get_response.url = "https://192.168.0.1/evil"
    mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
    mock_get_response.__aexit__ = AsyncMock(return_value=False)

    mock_get_session = MagicMock()
    mock_get_session.get.return_value = mock_get_response
    mock_get_session.__aenter__ = AsyncMock(return_value=mock_get_session)
    mock_get_session.__aexit__ = AsyncMock(return_value=False)

    sessions = [mock_head_session, mock_get_session]
    session_iter = iter(sessions)

    call_count = 0

    async def fake_validate(url):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return True, ""
        return False, "Private IP blocked"

    with (
        patch("app.utils.url_helper.aiohttp.ClientSession", side_effect=lambda: next(session_iter)),
        patch("app.utils.url_helper.validate_url", side_effect=fake_validate),
    ):
        with pytest.raises(SSRFValidationError):
            await resolve_redirects("https://on.soundcloud.com/abc")
