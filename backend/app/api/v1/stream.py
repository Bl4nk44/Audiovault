import asyncio
import logging
import os
from collections.abc import AsyncIterator
from typing import Annotated
from urllib.parse import urlparse

import aiofiles
import httpx
import mutagen.mp4
import yt_dlp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from mutagen import File as MutagenFile
from mutagen.id3 import APIC, ID3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.subsonic.handlers.media import ALLOWED_IMAGE_DOMAINS
from app.core.cache import cache_manager
from app.core.executors import stream_executor
from app.db.database import get_db
from app.models.album import Album
from app.models.download import Download
from app.models.track import Track
from app.services.deezer_service import DeezerService
from app.services.youtube_service import YouTubeService
from app.utils.ydl import apply_proxy

router = APIRouter()
logger = logging.getLogger(__name__)


async def _resolve_local_cover_file(directory: str) -> tuple[bytes | None, str | None]:
    """Check for local cover files and return content + mime type."""
    cover_names = ["cover.jpg", "folder.jpg", "cover.png", "folder.png", "artwork.jpg", "artwork.png"]
    for name in cover_names:
        cover_path = os.path.join(directory, name)  # nosemgrep: path-traversal  # directory from DB, name is hardcoded
        if os.path.exists(cover_path):
            try:
                async with aiofiles.open(cover_path, "rb") as f:
                    content = await f.read()
                    mime = "image/jpeg" if name.endswith(".jpg") else "image/png"
                    return content, mime
            except Exception as e:
                logger.warning(f"Failed to read local cover {cover_path}: {e}")
    return None, None


def _extract_art_flac(audio) -> tuple[bytes | None, str | None]:
    if hasattr(audio, "pictures") and audio.pictures:
        p = audio.pictures[0]
        return p.data, p.mime
    return None, None


def _extract_art_id3(audio) -> tuple[bytes | None, str | None]:
    if hasattr(audio, "tags") and isinstance(audio.tags, ID3):
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                return tag.data, tag.mime  # type: ignore
    return None, None


def _extract_art_mp4(audio) -> tuple[bytes | None, str | None]:
    if hasattr(audio, "tags") and "covr" in audio.tags:
        covers = audio.tags["covr"]
        if covers:
            c = covers[0]
            mime = "image/jpeg"
            if c.imageformat == mutagen.mp4.MP4Cover.FORMAT_PNG:
                mime = "image/png"
            return bytes(c), mime
    return None, None


def _extract_art_sync(path: str) -> tuple[bytes | None, str | None]:
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


async def _extract_embedded_cover_art(file_path: str) -> tuple[bytes | None, str | None]:
    """Run mutagen extraction in executor."""
    import functools

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(stream_executor, functools.partial(_extract_art_sync, file_path))


async def _resolve_track_path(db: AsyncSession, track_id: str) -> tuple[Track | None, str | None]:
    """Resolve Track and filesystem path."""
    import uuid

    track: Track | None = None

    try:
        t_uuid = uuid.UUID(str(track_id))
        # 1. Try to find track by local UUID
        result = await db.execute(select(Track).where(Track.id == t_uuid))
        track = result.scalar_one_or_none()

        if not track:
            # Try finding by download if track_id is actually download_id
            result_dl = await db.execute(select(Download).where(Download.id == t_uuid))
            dl_found: Download | None = result_dl.scalar_one_or_none()
            if dl_found and dl_found.track:
                track = dl_found.track
    except ValueError:
        # Not a UUID — try matching by deezer_id (numeric string from browse results)
        result = await db.execute(select(Track).where(Track.deezer_id == track_id))
        track = result.scalar_one_or_none()

    if not track:
        return None, None

    # 2. Resolve local file path via Download
    file_path: str | None = None
    # Cast track.id to str because Download.track_id is String
    dl_res = await db.execute(select(Download).where(Download.track_id == track.id))
    download_item: Download | None = dl_res.scalars().first()

    if download_item and download_item.file_path and os.path.exists(download_item.file_path):
        file_path = download_item.file_path

    return track, file_path


async def _get_album_art_redirect(track: Track, db: AsyncSession) -> RedirectResponse | None:
    if not track.album_id:
        return None
    result = await db.execute(select(Album).where(Album.id == track.album_id))
    album = result.scalar_one_or_none()
    if not (album and album.images):
        return None
    url = album.images.get("300") or album.images.get("640")
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc in ALLOWED_IMAGE_DOMAINS:
        return RedirectResponse(url)  # nosemgrep: python.fastapi.web.tainted-redirect-fastapi.tainted-redirect-fastapi
    return None


@router.get("/{track_id}/cover", responses={404: {"description": "Not found"}})
async def get_track_cover(track_id: str, db: Annotated[AsyncSession, Depends(get_db)] = ...):
    """
    Get cover art for a track.
    Priority: Local File -> Embedded Art -> Linked Album Art
    """
    track, file_path = await _resolve_track_path(db, track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if file_path:
        directory = os.path.dirname(file_path)
        content, mime = await _resolve_local_cover_file(directory)
        if content:
            return Response(content=content, media_type=mime)
        content, mime = await _extract_embedded_cover_art(file_path)
        if content:
            return Response(content=content, media_type=mime)

    redirect = await _get_album_art_redirect(track, db)
    if redirect:
        return redirect

    raise HTTPException(status_code=404, detail="No cover art found")


@router.get(
    "/album/{album_id}/cover",
    responses={400: {"description": "Bad request"}, 404: {"description": "Not found"}},
)
async def get_album_cover(album_id: str, db: Annotated[AsyncSession, Depends(get_db)] = ...):
    """Get cover art for an album."""
    import uuid

    try:
        a_uuid = uuid.UUID(str(album_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid album ID") from None

    result = await db.execute(select(Album).where(Album.id == a_uuid))
    album = result.scalar_one_or_none()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Priority: 300px -> 640px -> generic url
    url = (album.images or {}).get("300") or (album.images or {}).get("640") or (album.images or {}).get("url")
    if url:
        parsed = urlparse(url)
        if parsed.netloc in ALLOWED_IMAGE_DOMAINS:
            return RedirectResponse(
                url
            )  # nosemgrep: python.fastapi.web.tainted-redirect-fastapi.tainted-redirect-fastapi

    raise HTTPException(status_code=404, detail="No cover art found")


async def _youtube_search_url(query: str) -> str | None:
    """Search YouTube and return the first watch URL, or None."""
    try:
        import functools

        loop = asyncio.get_event_loop()
        youtube_service = YouTubeService()
        results = await loop.run_in_executor(stream_executor, functools.partial(youtube_service.search, query, limit=1))
        if results:
            return f"https://www.youtube.com/watch?v={results[0]['id']}"
    except Exception as e:
        logger.error(f"YouTube search failed for '{query}': {e}")
    return None


async def _lookup_track_by_external_id(db: AsyncSession, track_id: str) -> Track | None:
    """Find a track by any of its known external platform IDs."""
    for col in (Track.spotify_id, Track.deezer_id, Track.youtube_id):
        result = await db.execute(select(Track).where(col == track_id))
        db_track = result.scalar_one_or_none()
        if db_track:
            return db_track
    return None


async def _youtube_url_from_track(db_track: Track) -> str | None:
    """Resolve a YouTube URL from a DB track, by direct ID or title/artist search."""
    if db_track.youtube_id:
        return f"https://www.youtube.com/watch?v={db_track.youtube_id}"
    if db_track.title and db_track.artist:
        return await _youtube_search_url(f"{db_track.artist} - {db_track.title}")
    return None


async def _youtube_url_from_deezer(track_id: str) -> str | None:
    """For a numeric ID, resolve via Deezer public API then YouTube search."""
    if not track_id.isdigit():
        return None
    deezer_track = await DeezerService().get_track(track_id)
    if not deezer_track:
        return None
    return await _youtube_search_url(f"{deezer_track['artist']} - {deezer_track['title']}")


async def _resolve_stream_url(track_id: str, db: AsyncSession) -> str:
    cached_url = await cache_manager.get(f"stream_url:{track_id}")
    if cached_url:
        return cached_url

    # 1. Direct YouTube ID (exactly 11 alphanumeric chars)
    if len(track_id) == 11 and track_id.replace("-", "").replace("_", "").isalnum():
        youtube_url: str | None = f"https://www.youtube.com/watch?v={track_id}"
    else:
        # 2. Look up track in DB by any known external ID, else 3. fall back to Deezer
        db_track = await _lookup_track_by_external_id(db, track_id)
        if db_track:
            youtube_url = await _youtube_url_from_track(db_track)
        else:
            youtube_url = await _youtube_url_from_deezer(track_id)

        if not youtube_url:
            raise HTTPException(status_code=404, detail="Stream not found")

    await cache_manager.set(f"stream_url:{track_id}", youtube_url, expire=3600)
    return youtube_url


def _build_ydl_format() -> str:
    """iOS Safari cannot decode opus/webm — prefer AAC (m4a), fall back to anything."""
    return "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"


async def _extract_direct_url(youtube_url: str) -> tuple[str, dict, str]:
    ydl_opts = {
        "format": _build_ydl_format(),
        "quiet": True,
        "no_warnings": True,
    }
    apply_proxy(ydl_opts)

    import functools

    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Note: extract_info can still block significantly, so executor is crucial
        info_extractor = functools.partial(ydl.extract_info, youtube_url, download=False)
        info = await loop.run_in_executor(stream_executor, info_extractor)
        ext = info.get("ext", "m4a")
        mime = {
            "m4a": "audio/mp4",
            "mp4": "audio/mp4",
            "webm": "audio/webm",
            "opus": "audio/webm",
            "mp3": "audio/mpeg",
        }.get(ext, "audio/mp4")
        return info["url"], info.get("http_headers", {}), mime


@router.get(
    "/{track_id}.mp3",
    responses={404: {"description": "Not found"}, 500: {"description": "Internal server error"}},
)
async def stream_track(
    track_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    client: httpx.AsyncClient | None = None
    upstream: httpx.Response | None = None
    try:
        youtube_url = await _resolve_stream_url(track_id, db)
        url, headers, media_type = await _extract_direct_url(youtube_url)

        # Forward Range header from browser for seeking support
        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0))
        upstream_req = client.build_request("GET", url, headers=headers)
        upstream = await client.send(upstream_req, stream=True, follow_redirects=True)

        if upstream.status_code >= 400:
            await upstream.aclose()
            await client.aclose()
            upstream = None
            client = None
            await cache_manager.delete(f"stream_url:{track_id}")
            raise HTTPException(status_code=502, detail="Upstream stream unavailable")

        response_headers = {}
        if upstream.status_code == 206 or upstream.headers.get("accept-ranges") == "bytes":
            response_headers["Accept-Ranges"] = "bytes"
        for h in ("content-range", "content-length"):
            if h in upstream.headers:
                response_headers[h.title()] = upstream.headers[h]

        async def body(client: httpx.AsyncClient, upstream: httpx.Response) -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_bytes(64 * 1024):
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        status_code = 206 if upstream.status_code == 206 else 200
        return StreamingResponse(
            body(client, upstream), status_code=status_code, headers=response_headers, media_type=media_type
        )
    except HTTPException:
        if upstream is not None:
            await upstream.aclose()
        if client is not None:
            await client.aclose()
        raise
    except Exception as e:
        if upstream is not None:
            await upstream.aclose()
        if client is not None:
            await client.aclose()
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail="Internal streaming error") from e
