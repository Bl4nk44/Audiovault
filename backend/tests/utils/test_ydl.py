"""Tests for the yt-dlp proxy injection helper."""

from unittest.mock import patch

from app.utils.ydl import apply_proxy


def test_apply_proxy_noop_when_unset():
    with patch("app.utils.ydl.settings") as mock_settings:
        mock_settings.DOWNLOAD_PROXY = None
        opts = {"quiet": True}
        result = apply_proxy(opts)
    assert "proxy" not in result
    assert result is opts  # returns the same dict


def test_apply_proxy_injects_proxy_when_set():
    with patch("app.utils.ydl.settings") as mock_settings:
        mock_settings.DOWNLOAD_PROXY = "socks5://10.0.0.1:1080"
        result = apply_proxy({"quiet": True})
    assert result["proxy"] == "socks5://10.0.0.1:1080"
    assert result["quiet"] is True
