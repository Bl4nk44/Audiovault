from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import yt_dlp
import aiohttp
import asyncio
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService

import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{track_id}.mp3")
async def stream_track(track_id: str):
    try:
        youtube_url = await _resolve_stream_url(track_id)
        url, headers = await _extract_direct_url(youtube_url)
        return StreamingResponse(_stream_content(url, headers), media_type="audio/mpeg")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _resolve_stream_url(track_id: str) -> str:
    from app.core.cache import cache_manager

    cached_url = await cache_manager.get(f"stream_url:{track_id}")
    if cached_url:
        return cached_url

    youtube_url = None
    if len(track_id) == 11:
        # Assume YouTube
        youtube_url = f"https://www.youtube.com/watch?v={track_id}"
    else:
        # Assume Spotify, resolve to YouTube
        # Note: Services should ideally be async or run in executor
        spotify_service = SpotifyService()
        track = spotify_service.get_track(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        # Search on YouTube
        youtube_service = YouTubeService()
        query = f"{track['artist']} - {track['title']}"
        results = youtube_service.search(query, limit=1)
        if not results:
            raise HTTPException(status_code=404, detail="Stream not found")

        youtube_url = f"https://www.youtube.com/watch?v={results[0]['id']}"

    # Cache the resolved URL (valid for 1 hour)
    await cache_manager.set(f"stream_url:{track_id}", youtube_url, expire=3600)
    return youtube_url


async def _extract_direct_url(youtube_url: str) -> tuple[str, dict]:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
    }

    from app.core.executors import stream_executor

    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await loop.run_in_executor(
            stream_executor, lambda: ydl.extract_info(youtube_url, download=False)
        )
        return info["url"], info.get("http_headers", {})


async def _stream_content(url: str, headers: dict = None):
    async with aiohttp.ClientSession() as session:
        # Pass headers to the request to avoid 403 Forbidden from strict servers (Youtube)
        async with session.get(url, headers=headers) as response:
            async for chunk in response.content.iter_chunked(8192):
                yield chunk
