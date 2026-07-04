"""Shared helpers for building yt-dlp options."""

from typing import Any

from app.core.config import settings


def apply_proxy(ydl_opts: dict[str, Any]) -> dict[str, Any]:
    """Inject the configured DOWNLOAD_PROXY into yt-dlp options.

    No-op when DOWNLOAD_PROXY is unset. Returns the same dict so callers
    can use it inline: ``yt_dlp.YoutubeDL(apply_proxy(opts))``.
    """
    if settings.DOWNLOAD_PROXY:
        ydl_opts["proxy"] = settings.DOWNLOAD_PROXY
    return ydl_opts
