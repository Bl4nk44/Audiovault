import asyncio
import logging
import os
from typing import Optional

import aiofiles
import aiohttp
import mutagen.mp4
import yt_dlp
from app.core.cache import cache_manager
from app.core.executors import stream_executor
from app.db.database import get_db
from app.models.album import Album
from app.models.download import Download
from app.models.track import Track
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from mutagen import File as MutagenFile
from mutagen.id3 import APIC, ID3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def _resolve_local_cover_file(directory: str) -> tuple[Optional[bytes], Optional[str]]:
    """Check for local cover files and return content + mime type."""
    cover_names = ["cover.jpg", "folder.jpg", "cover.png", "folder.png", "artwork.jpg", "artwork.png"]
    for name in cover_names:
        cover_path = os.path.join(directory, name)
        if os.path.exists(cover_path):
            try:
                async with aiofiles.open(cover_path, "rb") as f:
                    content = await f.read()
                    mime = "image/jpeg" if name.endswith(".jpg") else "image/png"
                    return content, mime
            except Exception as e:
                logger.warning(f"Failed to read local cover {cover_path}: {e}")
    return None, None


def _extract_art_flac(audio) -> tuple[Optional[bytes], Optional[str]]:
    if hasattr(audio, "pictures") and audio.pictures:
        p = audio.pictures[0]
        return p.data, p.mime
    return None, None


def _extract_art_id3(audio) -> tuple[Optional[bytes], Optional[str]]:
    if hasattr(audio, "tags") and isinstance(audio.tags, ID3):
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                return tag.data, tag.mime  # type: ignore
    return None, None


def _extract_art_mp4(audio) -> tuple[Optional[bytes], Optional[str]]:
    if hasattr(audio, "tags") and "covr" in audio.tags:
        covers = audio.tags["covr"]
        if covers:
            c = covers[0]
            mime = "image/jpeg"
            if c.imageformat == mutagen.mp4.MP4Cover.FORMAT_PNG:
                mime = "image/png"
            return bytes(c), mime
    return None, None


def _extract_art_sync(path: str) -> tuple[Optional[bytes], Optional[str]]:
    """Synchronous mutagen extraction logic."""
    try:
        audio = MutagenFile(path)
        if not audio:
            return None, None

        # Try each strategy
        data, mime = _extract_art_flac(audio)
        if data:
            return data, mime

        data, mime = _extract_art_id3(audio)
        if data:
            return data, mime

        data, mime = _extract_art_mp4(audio)
        if data:
            return data, mime

    except Exception as e:
        logger.debug(f"Mutagen extraction failed for {path}: {e}")

    return None, None


async def _extract_embedded_cover_art(file_path: str) -> tuple[Optional[bytes], Optional[str]]:
    """Run mutagen extraction in executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(stream_executor, lambda: _extract_art_sync(file_path))


async def _resolve_track_path(db: AsyncSession, track_id: str) -> tuple[Optional[Track], Optional[str]]:
    """Resolve Track and filesystem path."""
    import uuid

    try:
        t_uuid = uuid.UUID(str(track_id))
    except ValueError:
        return None, None

    # 1. Try to find track content
    result = await db.execute(select(Track).where(Track.id == t_uuid))
    track: Track | None = result.scalar_one_or_none()

    if not track:
        # Try finding by download if track_id is actually download_id
        result_dl = await db.execute(select(Download).where(Download.id == t_uuid))
        dl_found: Download | None = result_dl.scalar_one_or_none()
        if dl_found and dl_found.track:
            track = dl_found.track
        else:
            return None, None

    # 2. Resolve local file path via Download
    file_path: str | None = None
    # Cast track.id to str because Download.track_id is String
    dl_res = await db.execute(select(Download).where(Download.track_id == track.id))
    download_item: Download | None = dl_res.scalars().first()

    if download_item and download_item.file_path and os.path.exists(download_item.file_path):
        file_path = download_item.file_path

    return track, file_path


@router.get("/{track_id}/cover")
async def get_track_cover(track_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get cover art for a track.
    Priority: Local File -> Embedded Art -> Linked Album Art
    """
    track, file_path = await _resolve_track_path(db, track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if file_path:
        directory = os.path.dirname(file_path)

        # 1. Local Files
        content, mime = await _resolve_local_cover_file(directory)
        if content:
            return Response(content=content, media_type=mime)

        # 2. Embedded Art
        content, mime = await _extract_embedded_cover_art(file_path)
        if content:
            return Response(content=content, media_type=mime)

    # 3. Fallback to Album art if linked
    if track.album_id:
        result = await db.execute(select(Album).where(Album.id == track.album_id))
        album = result.scalar_one_or_none()
        if album and album.images:
            url = (album.images or {}).get("300") or (album.images or {}).get("640")
            if url:
                return RedirectResponse(url)

    # 404 if no file source or art found
    raise HTTPException(status_code=404, detail="No cover art found")


@router.get("/album/{album_id}/cover")
async def get_album_cover(album_id: str, db: AsyncSession = Depends(get_db)):
    """Get cover art for an album."""
    import uuid

    try:
        a_uuid = uuid.UUID(str(album_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid album ID")

    result = await db.execute(select(Album).where(Album.id == a_uuid))
    album = result.scalar_one_or_none()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

        # Priority: 300px -> 640px -> generic url
        url = (album.images or {}).get("300") or (album.images or {}).get("640") or (album.images or {}).get("url")
        if url:
            return RedirectResponse(url)

    raise HTTPException(status_code=404, detail="No cover art found")


def _resolve_stream_url_sync(track_info: dict) -> Optional[str]:
    """Sync helper for YouTube service search."""
    try:
        youtube_service = YouTubeService()
        query = f"{track_info['artist']} - {track_info['title']}"
        results = youtube_service.search(query, limit=1)
        if results:
            return f"https://www.youtube.com/watch?v={results[0]['id']}"
    except Exception as e:
        logger.error(f"YouTube search failed: {e}")
    return None


def _get_spotify_track_sync(track_id: str) -> Optional[dict]:
    try:
        spotify_service = SpotifyService()
        return spotify_service.get_track(track_id)
    except Exception as e:
        logger.error(f"Spotify lookup failed: {e}")
    return None


async def _resolve_stream_url(track_id: str) -> str:
    cached_url = await cache_manager.get(f"stream_url:{track_id}")
    if cached_url:
        return cached_url

    youtube_url = None
    if len(track_id) == 11:
        youtube_url = f"https://www.youtube.com/watch?v={track_id}"
    else:
        # Spotify -> YouTube resolution
        loop = asyncio.get_event_loop()

        # 1. Get Spotify Metadata
        track_info = await loop.run_in_executor(stream_executor, lambda: _get_spotify_track_sync(track_id))

        if not track_info:
            raise HTTPException(status_code=404, detail="Track not found")

        # 2. Search on YouTube
        found_url = await loop.run_in_executor(stream_executor, lambda: _resolve_stream_url_sync(track_info))

        if not found_url:
            raise HTTPException(status_code=404, detail="Stream not found")
        youtube_url = found_url

    await cache_manager.set(f"stream_url:{track_id}", youtube_url, expire=3600)
    return youtube_url


async def _extract_direct_url(youtube_url: str) -> tuple[str, dict]:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
    }

    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Note: extract_info can still block significantly, so executor is crucial
        info = await loop.run_in_executor(stream_executor, lambda: ydl.extract_info(youtube_url, download=False))
        return info["url"], info.get("http_headers", {})


async def _stream_content(url: str, headers: Optional[dict] = None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            async for chunk in response.content.iter_chunked(8192):
                yield chunk


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
        raise HTTPException(status_code=500, detail=str(e)) from e
