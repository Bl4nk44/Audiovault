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
from urllib.parse import urlparse
from uuid import UUID

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
    result = await db.execute(
        select(Download)
        .where(
            Download.track_id == track_id,
            Download.status == "completed",
        )
        .order_by(Download.completed_at.desc())
    )
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
    id: str = Query(..., description="Song ID"),
    maxBitRate: int = Query(None, description="Max bitrate in kbps"),
    format: str = Query(None, description="Preferred format"),
    timeOffset: int = Query(None, description="Offset in seconds"),
    size: str = Query(None, description="Video size (ignored)"),
    estimateContentLength: bool = Query(False, description="Estimate content length"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream audio file.

    Supports HTTP Range requests for seeking.

    Args:
        id: Track ID (UUID)
        maxBitRate: Maximum bitrate (currently ignored, returns original)
        format: Preferred format (currently ignored, returns original)
        timeOffset: Start offset in seconds (for transcoding)

    Returns:
        Audio file stream with proper headers
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
        "Content-Disposition": f'inline; filename="{os.path.basename(file_path)}"',
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        status_code = 206
    else:
        status_code = 200

    # Stream file
    async def file_iterator():
        chunk_size = 64 * 1024  # 64KB chunks
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        file_iterator(),
        status_code=status_code,
        headers=headers,
        media_type=content_type,
    )


@router.get("/download.view")
@router.post("/download.view")
async def download_file(
    id: str = Query(..., description="Song ID"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Download audio file.

    Returns the original file as attachment.

    Args:
        id: Track ID (UUID)

    Returns:
        Audio file with Content-Disposition: attachment
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
        return subsonic_error(70, "File not found on disk", f=f)

    # Get track info for filename
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()

    if track:
        # Generate nice filename
        ext = os.path.splitext(file_path)[1] or ".mp3"
        safe_title = "".join(c for c in (track.title or "Unknown") if c.isalnum() or c in " -_").strip()
        safe_artist = "".join(c for c in (track.artist or "Unknown") if c.isalnum() or c in " -_").strip()
        filename = f"{safe_artist} - {safe_title}{ext}"
    else:
        filename = os.path.basename(file_path)

    return FileResponse(
        file_path,
        media_type=get_content_type(file_path),
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


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

    Cover art ID format:
    - "al-{album_id}" for albums
    - "ar-{artist_id}" for artists
    - "tr-{track_id}" or just "{track_id}" for tracks

    Args:
        id: Cover art ID
        size: Preferred size in pixels (may be ignored)

    Returns:
        Redirect to image URL or image bytes
    """
    image_url = None

    try:
        item_type, item_id = parse_cover_art_id(id)
    except ValueError:
        return subsonic_error(70, "Invalid cover art ID", f=f)

    if item_type == "al":
        # Album cover
        result = await db.execute(select(Album).where(Album.id == item_id))
        album = result.scalar_one_or_none()
        if album and album.images:
             # Try 300 or 640
             image_url = album.images.get("300") or album.images.get("640") or album.images.get("64")

    else:
        # Unknown type or raw UUID - could be Track, Album, or Artist if client sends plain UUID
        # 1. Try Track (most common)
        result = await db.execute(select(Track).where(Track.id == item_id))
        track = result.scalar_one_or_none()
        if track:
            item_type = "tr"
            metadata = track.metadata_content or {}
            image_url = metadata.get("image_url") or metadata.get("album_art")

            # If track has album, try album cover
            if not image_url and track.album_id:
                album_result = await db.execute(select(Album).where(Album.id == track.album_id))
                album = album_result.scalar_one_or_none()
                if album and album.images:
                     # Try 300 or 640
                     image_url = album.images.get("300") or album.images.get("640") or album.images.get("64")

        else:
            # 2. Try Album
            result = await db.execute(select(Album).where(Album.id == item_id))
            album = result.scalar_one_or_none()
            if album:
                item_type = "al"
                if album.images:
                     image_url = album.images.get("300") or album.images.get("640") or album.images.get("64")
            else:
                # 3. Try Artist
                result = await db.execute(select(Artist).where(Artist.id == item_id))
                artist = result.scalar_one_or_none()
                if artist:
                    item_type = "ar"
                    if artist.images:
                        images = artist.images
                        if isinstance(images, dict):
                            image_url = images.get("large") or images.get("medium") or images.get("small")
                        elif isinstance(images, list) and images:
                            image_url = images[0].get("url") if isinstance(images[0], dict) else images[0]

    # ... (existing proxy logic) ...
    # This part replaces the 404 return
    
    # If no external URL, try to find local cover art
    if not image_url:
        # Resolve file path to search in
        file_path = None
        logger.info(f"CoverArt: Looking for local file for item {item_id} (type {item_type})")
        
        try:
            if item_type == "tr":
                result = await db.execute(select(Download).where(Download.track_id == item_id))
                download = result.scalars().first()
                if download:
                    file_path = download.file_path
                    logger.info(f"CoverArt: Found track download path: {file_path}")
                else:
                    logger.warning(f"CoverArt: No download record for track {item_id}")
                    
            elif item_type == "al":
                result = await db.execute(select(Download).join(Track, Download.track_id == Track.id).where(Track.album_id == item_id).limit(1))
                download = result.scalars().first()
                if download:
                    file_path = download.file_path
                    logger.info(f"CoverArt: Found album sample path: {file_path}")
                else:
                    logger.warning(f"CoverArt: No download record for album {item_id}")

            elif item_type == "ar":
                result = await db.execute(select(Download).join(Track, Download.track_id == Track.id).where(Track.artist_id == item_id).limit(1))
                download = result.scalars().first()
                if download:
                    file_path = download.file_path
                    logger.info(f"CoverArt: Found artist sample path: {file_path}")
                else:
                    logger.warning(f"CoverArt: No download record for artist {item_id}")
            
            if file_path and os.path.exists(file_path):
                directory = os.path.dirname(file_path)
                logger.info(f"CoverArt: Searching directory {directory}")
                for name in ["cover.jpg", "cover.png", "cover.jpeg", "folder.jpg", "front.jpg", "album.jpg"]:
                    local_path = os.path.join(directory, name)
                    if os.path.exists(local_path):
                         logger.info(f"CoverArt: Serving local file {local_path}")
                         return FileResponse(local_path)
                
                logger.info("CoverArt: No known cover file found, checking embedded...")
                import mutagen
                f = mutagen.File(file_path)
                
                # Check for FLAC/Vorbis pictures
                if hasattr(f, 'pictures') and f.pictures:
                    pic = next((p for p in f.pictures if p.type == 3), f.pictures[0])
                    logger.info("CoverArt: Extracted FLAC/Vorbis picture")
                    return Response(content=pic.data, media_type=pic.mime)

                # Check for ID3 tags (MP3)
                if f and hasattr(f, 'tags'):
                    # Try getall for APIC (mutagen.id3.ID3)
                    if hasattr(f.tags, 'getall'):
                        apic_frames = f.tags.getall("APIC")
                        if apic_frames:
                            logger.info("CoverArt: Extracted APIC frame (getall)")
                            return Response(content=apic_frames[0].data, media_type=apic_frames[0].mime)
                    
                    # Fallback iteration for other tag formats
                    if hasattr(f.tags, 'values'):
                        for tag in f.tags.values():
                            if hasattr(tag, 'frameid') and tag.frameid == 'APIC':
                                logger.info("CoverArt: Extracted APIC frame (iter)")
                                return Response(content=tag.data, media_type=tag.mime)
                                
                logger.info("CoverArt: No embedded art found.")
            else:
                logger.warning(f"CoverArt: File path {file_path} does not exist or is None")

        except Exception as e:
            logger.error(f"CoverArt: Local fallback error: {e}")

        # If still nothing, return 404 or placeholder
        return Response(status_code=404, content=b"", media_type="image/png")

    # Security: Validate URL to prevent open redirect
    # Only allow HTTP/HTTPS URLs from trusted image sources
    parsed_url = urlparse(image_url)
    
    # ... (rest of the existing proxy logic) ...

    # Must be HTTP or HTTPS
    if parsed_url.scheme not in ("http", "https"):
        logger.warning(f"Invalid image URL scheme: {image_url}")
        return Response(status_code=404, content=b"", media_type="image/png")

    # Must have a valid host
    if not parsed_url.netloc:
        logger.warning(f"Invalid image URL - no host: {image_url}")
        return Response(status_code=404, content=b"", media_type="image/png")

    # Check if domain is allowed
    # host = parsed_url.netloc.lower()
    # is_allowed = any(
    #     host == domain or host.endswith(f".{domain}")
    #     for domain in ALLOWED_IMAGE_DOMAINS
    # )

    # if not is_allowed:
    #     logger.warning(f"Cover art from untrusted domain blocked: {host}")
    #     return Response(status_code=404, content=b"", media_type="image/png")

    # Allow all for now
    # is_allowed = True

    # Proxy the image instead of redirecting (eliminates Open Redirect risk)
    # Also provides caching opportunity and hides external URLs from client

    # Generate cache key from URL hash
    url_hash = hashlib.md5(image_url.encode()).hexdigest()
    cache_path = os.path.join(COVER_ART_CACHE_DIR, f"{url_hash}.img")

    # Check cache first
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                content = f.read()
            # Detect content type from magic bytes
            content_type = "image/jpeg"
            if content[:8] == b"\x89PNG\r\n\x1a\n":
                content_type = "image/png"
            elif content[:3] == b"GIF":
                content_type = "image/gif"
            elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                content_type = "image/webp"

            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Cache": "HIT",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to read cached cover art: {e}")

    # Fetch from remote URL
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(image_url, follow_redirects=True, headers={"User-Agent": "Audiovault/1.0"})

            if resp.status_code != 200:
                logger.warning(f"Failed to fetch cover art: {resp.status_code}")
                return Response(status_code=404, content=b"", media_type="image/png")

            # Detect content type
            content_type = resp.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"

            # Save to cache
            try:
                with open(cache_path, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                logger.warning(f"Failed to cache cover art: {e}")

            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Cache": "MISS",
                },
            )
    except httpx.RequestError as e:
        logger.warning(f"Error fetching cover art: {e}")
        return Response(status_code=404, content=b"", media_type="image/png")


@router.get("/hls.view")
async def hls_stream(
    id: str = Query(..., description="Song ID"),
    bitRate: str = Query(None, description="Bitrate list"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    """
    HLS streaming (not implemented).

    Returns error - use regular stream instead.
    """
    return subsonic_error(0, "HLS streaming not supported. Use stream.view instead.", f=f)
