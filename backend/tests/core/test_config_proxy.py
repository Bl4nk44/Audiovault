"""Tests for DOWNLOAD_PROXY setting validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_download_proxy_default_none():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.DOWNLOAD_PROXY is None


def test_download_proxy_empty_string_becomes_none():
    # docker-compose commonly passes DOWNLOAD_PROXY= (empty) when unset
    s = Settings(_env_file=None, DOWNLOAD_PROXY="")  # type: ignore[call-arg]
    assert s.DOWNLOAD_PROXY is None


@pytest.mark.parametrize(
    "url",
    [
        "http://privoxy:8118",
        "https://proxy.local:3128",
        "socks4://10.0.0.1:1080",
        "socks5://user:pass@10.0.0.1:1080",
        "socks5h://tor:9050",
    ],
)
def test_download_proxy_accepts_supported_schemes(url):
    s = Settings(_env_file=None, DOWNLOAD_PROXY=url)  # type: ignore[call-arg]
    assert s.DOWNLOAD_PROXY == url


@pytest.mark.parametrize("url", ["privoxy:8118", "ftp://x:21", "socks://x:1080"])
def test_download_proxy_rejects_unsupported_schemes(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DOWNLOAD_PROXY=url)  # type: ignore[call-arg]
