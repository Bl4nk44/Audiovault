"""
Media handlers for Subsonic API.

Handles streaming and media endpoints:
- stream.view
- download.view
- getCoverArt.view
"""

import hashlib
import logging
import os
from urllib.parse import quote, urlparse
from uuid import UUID

import aiofiles
import httpx
from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import get_content_type, parse_cover_art_id
from app.db.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from mutagen import File as MutagenFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Constants
MIME_JPEG = "image/jpeg"
MIME_PNG = "image/png"
MIME_GIF = "image/gif"
MIME_WEBP = "image/webp"
DESC_SONG_ID = "Song ID"


def safe_content_disposition(filename: str, disposition: str = "inline") -> str:
    """
    Create a Content-Disposition header value that's safe for non-ASCII filenames.

    Uses RFC 5987 encoding (filename*=UTF-8''...) for Unicode characters.
    Falls back to ASCII-only filename for compatibility.

    Args:
        filename: The filename (may contain Unicode)
        disposition: 'inline' or 'attachment'

    Returns:
        Properly encoded Content-Disposition header value
    """
    # Create ASCII-safe fallback (remove non-ASCII chars)
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii")
    if not ascii_filename:
        ascii_filename = "file"

    # Check if we need UTF-8 encoding
    try:
        filename.encode("ascii")
        # Pure ASCII - simple format works
        return f'{disposition}; filename="{filename}"'
    except UnicodeEncodeError:
        # Contains non-ASCII - use RFC 5987 format
        encoded_filename = quote(filename, safe="")
        return f"{disposition}; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"


# Cover art cache directory
COVER_ART_CACHE_DIR = os.environ.get("COVER_ART_CACHE_DIR", "/tmp/audiovault_cache/cover_art")
os.makedirs(COVER_ART_CACHE_DIR, exist_ok=True)

router = APIRouter()

# Whitelist of allowed image domains for cover art redirects
# This prevents open redirect vulnerabilities
ALLOWED_IMAGE_DOMAINS = {
    "i.scdn.co",  # Spotify
    "mosaic.scdn.co",  # Spotify
    "e-cdns-images.dzcdn.net",  # Deezer
    "cdns-images.dzcdn.net",  # Deezer
    "i.ytimg.com",  # YouTube
    "lh3.googleusercontent.com",  # Google
    "is1-ssl.mzstatic.com",  # Apple Music
    "is2-ssl.mzstatic.com",
    "is3-ssl.mzstatic.com",
    "is4-ssl.mzstatic.com",
    "is5-ssl.mzstatic.com",
    "coverartarchive.org",
    "archive.org",
    "lastfm.freetls.fastly.net",  # Last.fm
}


async def get_download_for_track(
    db: AsyncSession,
    track_id: UUID,
    user_id: UUID,
) -> Download | None:
    """
    Get completed download for a track.

    Args:
        db: Database session
        track_id: Track UUID
        user_id: User UUID

    Returns:
        Download instance or None
    """
    stmt = (
        select(Download)
        .where(Download.track_id == track_id, Download.status == "completed", Download.user_id == user_id)
        .order_by(Download.completed_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int]:
    """
    Parse HTTP Range header.

    Args:
        range_header: Range header value (e.g., "bytes=0-1000")
        file_size: Total file size

    Returns:
        Tuple of (start, end) byte positions
    """
    if not range_header:
        return 0, file_size - 1

    try:
        range_spec = range_header.replace("bytes=", "")
        if range_spec.startswith("-"):
            # Suffix range: -500 means last 500 bytes
            suffix_length = int(range_spec[1:])
            return max(0, file_size - suffix_length), file_size - 1
        elif range_spec.endswith("-"):
            # Open-ended range: 500- means from byte 500 to end
            start = int(range_spec[:-1])
            return start, file_size - 1
        else:
            # Explicit range: 0-499
            parts = range_spec.split("-")
            start = int(parts[0])
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            return start, min(end, file_size - 1)
    except (ValueError, IndexError):
        return 0, file_size - 1


@router.get("/stream.view")
@router.post("/stream.view")
async def stream(
    request: Request,
    id: str = Query(..., description=DESC_SONG_ID),
    max_bit_rate: int = Query(None, description="Max bitrate in kbps", alias="maxBitRate"),
    format: str = Query(None, description="Preferred format"),
    time_offset: int = Query(None, description="Offset in seconds", alias="timeOffset"),
    size: str = Query(None, description="Video size (ignored)"),
    estimate_content_length: bool = Query(False, description="Estimate content length", alias="estimateContentLength"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream audio file.

    Supports HTTP Range requests for seeking.
    Uses aiofiles for non-blocking I/O.
    """
    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid song ID", f=f)

    # Get download for this track
    download = await get_download_for_track(db, track_id, current_user.id)

    if not download:
        return subsonic_error(70, "Song not found or not downloaded", f=f)

    file_path = download.file_path

    if not file_path or not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return subsonic_error(70, "File not found on disk", f=f)

    file_size = os.path.getsize(file_path)
    content_type = get_content_type(file_path)

    # Handle Range requests
    range_header = request.headers.get("range")
    start, end = parse_range_header(range_header, file_size)

    content_length = end - start + 1

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": content_type,
        "Content-Length": str(content_length),
        "Content-Disposition": safe_content_disposition(os.path.basename(file_path), "inline"),
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        status_code = 206
    else:
        status_code = 200

    # Stream file asynchronously
    async def file_iterator():
        chunk_size = 64 * 1024  # 64KB chunks
        try:
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                remaining = content_length
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = await f.read(read_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        except Exception as e:
            logger.error(f"Error streaming file {file_path}: {e}")
            raise

    return StreamingResponse(
        file_iterator(),
        status_code=status_code,
        headers=headers,
        media_type=content_type,
    )


@router.get("/download.view")
@router.post("/download.view")
async def download_file(
    id: str = Query(..., description=DESC_SONG_ID),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid song ID", f=f)

    download = await get_download_for_track(db, track_id, current_user.id)

    if not download or not download.file_path or not os.path.exists(download.file_path):
        return subsonic_error(70, "Song not found or not downloaded", f=f)

    file_path = download.file_path

    # Get track info for filename
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()

    if track:
        ext = os.path.splitext(file_path)[1] or ".mp3"
        safe_title = "".join(c for c in (track.title or "Unknown") if c.isalnum() or c in " -_").strip()
        safe_artist = "".join(c for c in (track.artist or "Unknown") if c.isalnum() or c in " -_").strip()
        filename = f"{safe_artist} - {safe_title}{ext}"
    else:
        filename = os.path.basename(file_path)

    # Use FileResponse (FastAPI handles it efficiently via thread pool usually,
    # but for strict async we could implement custom)
    # FileResponse is generally acceptable for downloads as it uses run_in_executor internally
    return FileResponse(
        file_path,
        media_type=get_content_type(file_path),
        filename=filename,
        headers={
            "Content-Disposition": safe_content_disposition(filename, "attachment"),
        },
    )


# --- Helper functions for get_cover_art ---


async def _get_remote_image(image_url: str) -> Response | None:
    try:
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        cache_path = os.path.join(COVER_ART_CACHE_DIR, f"{url_hash}.img")

        # Check cache
        if os.path.exists(cache_path):
            async with aiofiles.open(cache_path, "rb") as f:
                content = await f.read()

            content_type = MIME_JPEG
            if content[:8] == b"\x89PNG\r\n\x1a\n":
                content_type = MIME_PNG
            elif content[:3] == b"GIF":
                content_type = MIME_GIF
            elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                content_type = MIME_WEBP

            return Response(content=content, media_type=content_type, headers={"X-Cache": "HIT"})

        # Fetch remote
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(image_url, follow_redirects=True, headers={"User-Agent": "Audiovault/1.0"})
            if resp.status_code != 200:
                return None

            content_type = resp.headers.get("content-type", MIME_JPEG)
            if not content_type.startswith("image/"):
                content_type = MIME_JPEG

            # Save to cache asynchronously
            async with aiofiles.open(cache_path, "wb") as f:
                await f.write(resp.content)

            return Response(content=resp.content, media_type=content_type, headers={"X-Cache": "MISS"})

    except Exception as e:
        logger.warning(f"Error fetching remote cover: {e}")
        return None


async def _resolve_local_file_path(db: AsyncSession, item_type: str, item_id: str) -> str | None:
    file_path = None
    if item_type == "tr":
        # Track
        result = await db.execute(select(Download).where(Download.track_id == item_id).limit(1))
        download = result.scalars().first()
        if download:
            file_path = download.file_path

    elif item_type == "al":
        # Album
        result = await db.execute(
            select(Download).join(Track, Download.track_id == Track.id).where(Track.album_id == item_id).limit(1)
        )
        download = result.scalars().first()
        if download:
            file_path = download.file_path

    elif item_type == "ar":
        # Artist
        result = await db.execute(
            select(Download).join(Track, Download.track_id == Track.id).where(Track.artist_id == item_id).limit(1)
        )
        download = result.scalars().first()
        if download:
            file_path = download.file_path

    if file_path and os.path.exists(file_path):
        return file_path
    return None


async def _check_local_cover_files(directory: str) -> Response | None:
    for name in ["cover.jpg", "cover.png", "cover.jpeg", "folder.jpg", "front.jpg", "album.jpg"]:
        local_path = os.path.join(directory, name)
        if os.path.exists(local_path):
            async with aiofiles.open(local_path, "rb") as f:
                content = await f.read()
            # Simple mime detection by extension
            mime = MIME_JPEG if name.endswith(("jpg", "jpeg")) else MIME_PNG
            return Response(content=content, media_type=mime)
    return None


def _try_extract_flac_art(audio_file) -> Response | None:
    if hasattr(audio_file, "pictures") and audio_file.pictures:
        pic = next((p for p in audio_file.pictures if p.type == 3), audio_file.pictures[0])
        return Response(content=pic.data, media_type=pic.mime)
    return None


def _try_extract_id3_art(audio_file) -> Response | None:
    if not hasattr(audio_file, "tags"):
        return None

    # Try getall for APIC (mutagen.id3.ID3)
    if hasattr(audio_file.tags, "getall"):
        apic_frames = audio_file.tags.getall("APIC")
        if apic_frames:
            return Response(content=apic_frames[0].data, media_type=apic_frames[0].mime)

    # Helper for other formats or older mutagen versions
    if hasattr(audio_file.tags, "values"):
        for tag in audio_file.tags.values():
            if hasattr(tag, "frameid") and tag.frameid == "APIC":
                return Response(content=tag.data, media_type=tag.mime)
    return None


def _extract_embedded_art(file_path: str) -> Response | None:
    # Mutagen is synchronous
    try:
        audio_file = MutagenFile(file_path)
        if not audio_file:
            return None

        resp = _try_extract_flac_art(audio_file)
        if resp:
            return resp

        return _try_extract_id3_art(audio_file)
    except Exception:
        pass
    return None


async def _resolve_album_image(db: AsyncSession, item_id: UUID) -> str | None:
    res = await db.execute(select(Album).where(Album.id == item_id))
    album = res.scalar_one_or_none()
    if album and album.images:
        return album.images.get("300") or album.images.get("640")
    return None


async def _resolve_track_image(db: AsyncSession, item_id: UUID) -> str | None:
    res = await db.execute(select(Track).where(Track.id == item_id))
    track = res.scalar_one_or_none()
    if not track:
        return None

    meta = track.metadata_content or {}
    image_url = meta.get("image_url") or meta.get("album_art")
    if image_url:
        return image_url

    if track.album_id:
        return await _resolve_album_image(db, track.album_id)
    return None


async def _resolve_artist_image(db: AsyncSession, item_id: UUID) -> str | None:
    res = await db.execute(select(Artist).where(Artist.id == item_id))
    artist = res.scalar_one_or_none()
    if artist and artist.images:
        if isinstance(artist.images, dict):
            return artist.images.get("medium")
        elif isinstance(artist.images, list) and artist.images:
            return artist.images[0].get("url")
    return None


async def _resolve_image_url(db: AsyncSession, item_type: str, item_id_str: str) -> str | None:
    """Helper to resolve remote image URL from DB"""
    try:
        item_id = UUID(item_id_str)
    except ValueError:
        return None

    if item_type == "al":
        return await _resolve_album_image(db, item_id)
    elif item_type == "tr":
        return await _resolve_track_image(db, item_id)
    elif item_type == "ar":
        return await _resolve_artist_image(db, item_id)
    return None


@router.get("/getCoverArt.view")
@router.post("/getCoverArt.view")
async def get_cover_art(
    id: str = Query(..., description="Cover art ID"),
    size: int = Query(None, description="Preferred image size"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cover art for album, track, or artist.
    """
    try:
        item_type, item_id = parse_cover_art_id(id)
    except ValueError:
        return subsonic_error(70, "Invalid cover art ID", f=f)

    # 1. Resolve Remote Image URL
    image_url = await _resolve_image_url(db, item_type, str(item_id))

    # 2. Try fetching remote if URL exists
    if image_url:
        parsed = urlparse(image_url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            resp = await _get_remote_image(image_url)
            if resp:
                return resp

    # 3. Fallback to Local Files
    file_path = await _resolve_local_file_path(db, item_type, str(item_id))

    if file_path:
        directory = os.path.dirname(file_path)

        # 3a. Check for cover.jpg etc
        resp = await _check_local_cover_files(directory)
        if resp:
            return resp

        # 3b. Check embedded art (running in thread pool to avoid blocking)
        import asyncio

        from app.core.executors import stream_executor

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(stream_executor, lambda: _extract_embedded_art(file_path))
        if resp:
            return resp

    # 4. Final fallback -> 404/Empty
    return Response(status_code=404, content=b"", media_type=MIME_PNG)


@router.get("/hls.view")
async def hls_stream(
    id: str = Query(..., description=DESC_SONG_ID),
    bit_rate: str = Query(None, description="Bitrate list", alias="bitRate"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    return subsonic_error(0, "HLS streaming not supported. Use stream.view instead.", f=f)
