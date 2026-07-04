"""Proxy wiring test for BaseMusicService._extract_info."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.base_music_service import BaseMusicService


class _Stub(BaseMusicService):
    def can_handle(self, url: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_extract_info_passes_proxy_to_ytdlp():
    captured: dict = {}

    def fake_ytdl(opts):
        captured.update(opts)
        instance = MagicMock()
        instance.extract_info.return_value = {"id": "x"}
        return instance

    with (
        patch("app.utils.ydl.settings") as mock_settings,
        patch("app.services.base_music_service.yt_dlp.YoutubeDL", side_effect=fake_ytdl),
    ):
        mock_settings.DOWNLOAD_PROXY = "socks5://10.0.0.1:1080"
        await _Stub()._extract_info("https://example.com/track")

    assert captured["proxy"] == "socks5://10.0.0.1:1080"
