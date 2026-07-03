"""Proxy wiring test for DownloadManager._get_ydl_options."""

from unittest.mock import MagicMock, patch

from app.services.download_manager import DownloadManager


def _make_download():
    download = MagicMock()
    download.id = 1
    download.source = "spotify"
    download.playlist_name = None
    download.user.username = "tester"
    download.user.preferences = {}
    return download


def _get_opts():
    manager = DownloadManager()
    ydl_opts, _ = manager._get_ydl_options(_make_download(), progress_hook=lambda d: None)
    return ydl_opts


def test_ydl_options_include_proxy_when_configured():
    with patch("app.utils.ydl.settings") as mock_settings:
        mock_settings.DOWNLOAD_PROXY = "http://privoxy:8118"
        ydl_opts = _get_opts()
    assert ydl_opts["proxy"] == "http://privoxy:8118"


def test_ydl_options_have_no_proxy_by_default():
    with patch("app.utils.ydl.settings") as mock_settings:
        mock_settings.DOWNLOAD_PROXY = None
        ydl_opts = _get_opts()
    assert "proxy" not in ydl_opts
