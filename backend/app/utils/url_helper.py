import ipaddress
import logging
import socket
from urllib.parse import urlparse

import aiohttp

from app.utils.log_sanitize import sanitize_log

logger = logging.getLogger(__name__)

# Allowed domains for music services
ALLOWED_DOMAINS: set[str] = {
    # Spotify
    "spotify.com",
    "open.spotify.com",
    "spotify.link",
    # Apple Music
    "music.apple.com",
    "itunes.apple.com",
    # Deezer
    "deezer.com",
    "deezer.page.link",
    # Tidal
    "tidal.com",
    "listen.tidal.com",
    # YouTube
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "music.youtube.com",
    # SoundCloud
    "soundcloud.com",
    "on.soundcloud.com",
    # Amazon Music
    "amazon.com",
    "music.amazon.com",
    "amzn.to",
}

# Private/internal IP ranges that should be blocked (SSRF protection)
BLOCKED_IP_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # "This" network
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


class SSRFValidationError(Exception):
    """Raised when URL validation fails due to SSRF protection."""

    pass


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is in a private/blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in BLOCKED_IP_NETWORKS)
    except ValueError:
        return False


def extract_domain(url: str) -> str:
    """Extract the base domain from a URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # Handle subdomains - extract base domain (last 2 parts)
    parts = hostname.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname


def is_allowed_domain(url: str) -> bool:
    """Check if URL's domain is in the allowed list."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Check exact match or if it's a subdomain of allowed domains
    for allowed in ALLOWED_DOMAINS:
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return True
    return False


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate a URL for SSRF protection.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check URL scheme
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid URL scheme: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    # Check domain whitelist
    if not is_allowed_domain(url):
        return False, f"Domain not allowed: {hostname}"

    # Resolve hostname to IP and check for private ranges
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        for addr_info in ip_addresses:
            ip_str = str(addr_info[4][0])
            if is_private_ip(ip_str):
                return False, f"Private IP address blocked: {ip_str}"
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"

    return True, ""


async def resolve_redirects(url: str) -> str:
    """
    Follows redirects to get the final URL.
    Validates URL for SSRF protection before making requests.
    """
    # Validate initial URL
    is_valid, error = validate_url(url)
    if not is_valid:
        logger.warning("SSRF validation failed for %s: %s", sanitize_log(url), sanitize_log(error))
        raise SSRFValidationError(error)

    try:
        async with aiohttp.ClientSession() as session:
            # Head request first to be faster/lighter
            async with session.head(url, allow_redirects=True) as response:
                final_url = str(response.url)

                # Validate final URL too (in case of open redirect)
                is_valid, error = validate_url(final_url)
                if not is_valid:
                    logger.warning(
                        "SSRF validation failed for redirect %s: %s",
                        sanitize_log(final_url),
                        sanitize_log(error),
                    )
                    raise SSRFValidationError(f"Redirect blocked: {error}")

                return final_url
    except SSRFValidationError:
        raise
    except Exception as e:
        logger.warning("Failed to resolve URL %s: %s", sanitize_log(url), sanitize_log(e))
        # If head fails (e.g. 405 Method Not Allowed), try GET
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True) as response:
                    final_url = str(response.url)

                    # Validate final URL
                    is_valid, error = validate_url(final_url)
                    if not is_valid:
                        raise SSRFValidationError(f"Redirect blocked: {error}")

                    return final_url
        except SSRFValidationError:
            raise
        except Exception as e2:
            logger.error("Failed to resolve URL %s with GET: %s", sanitize_log(url), sanitize_log(e2))
            return url
