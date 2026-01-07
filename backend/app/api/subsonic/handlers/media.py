"""
Media handlers for Subsonic API.

Handles streaming and media endpoints:
- stream.view
- download.view
- getCoverArt.view
"""

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
            Download.user_id == user_id,
            Download.status == "completed",
        )
        .order_by(Download.completed_at.desc())
    )
    return result.scalar_one_or_none()


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
        return subsonic_error(10, "Invalid song ID")
    
    # Get download for this track
    download = await get_download_for_track(db, track_id, current_user.id)
    
    if not download:
        return subsonic_error(70, "Song not found or not downloaded")
    
    file_path = download.file_path
    
    if not file_path or not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return subsonic_error(70, "File not found on disk")
    
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
        return subsonic_error(10, "Invalid song ID")
    
    # Get download for this track
    download = await get_download_for_track(db, track_id, current_user.id)
    
    if not download:
        return subsonic_error(70, "Song not found or not downloaded")
    
    file_path = download.file_path
    
    if not file_path or not os.path.exists(file_path):
        return subsonic_error(70, "File not found on disk")
    
    # Get track info for filename
    result = await db.execute(
        select(Track).where(Track.id == track_id)
    )
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
        }
    )


@router.get("/getCoverArt.view")
@router.post("/getCoverArt.view")
async def get_cover_art(
    id: str = Query(..., description="Cover art ID"),
    size: int = Query(None, description="Preferred image size"),
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
        return subsonic_error(70, "Invalid cover art ID")
    
    if item_type == "al":
        # Album cover
        result = await db.execute(
            select(Album).where(Album.id == item_id)
        )
        album = result.scalar_one_or_none()
        if album and album.images:
            # Get largest image or specific size
            images = album.images
            if isinstance(images, dict):
                image_url = images.get("large") or images.get("medium") or images.get("small")
            elif isinstance(images, list) and images:
                image_url = images[0].get("url") if isinstance(images[0], dict) else images[0]
    
    elif item_type == "ar":
        # Artist image
        result = await db.execute(
            select(Artist).where(Artist.id == item_id)
        )
        artist = result.scalar_one_or_none()
        if artist and artist.images:
            images = artist.images
            if isinstance(images, dict):
                image_url = images.get("large") or images.get("medium") or images.get("small")
            elif isinstance(images, list) and images:
                image_url = images[0].get("url") if isinstance(images[0], dict) else images[0]
    
    else:
        # Track or unknown - try track metadata
        result = await db.execute(
            select(Track).where(Track.id == item_id)
        )
        track = result.scalar_one_or_none()
        if track:
            metadata = track.metadata_content or {}
            image_url = metadata.get("image_url") or metadata.get("album_art")
            
            # If track has album, try album cover
            if not image_url and track.album_id:
                album_result = await db.execute(
                    select(Album).where(Album.id == track.album_id)
                )
                album = album_result.scalar_one_or_none()
                if album and album.images:
                    images = album.images
                    if isinstance(images, dict):
                        image_url = images.get("large") or images.get("medium") or images.get("small")
                    elif isinstance(images, list) and images:
                        image_url = images[0].get("url") if isinstance(images[0], dict) else images[0]
    
    if not image_url:
        # Return a default placeholder or 404
        return Response(
            status_code=404,
            content=b"",
            media_type="image/png",
        )
    
    # Security: Validate URL to prevent open redirect
    # Only allow HTTP/HTTPS URLs from trusted image sources
    parsed_url = urlparse(image_url)
    
    # Must be HTTP or HTTPS
    if parsed_url.scheme not in ("http", "https"):
        logger.warning(f"Invalid image URL scheme: {image_url}")
        return Response(status_code=404, content=b"", media_type="image/png")
    
    # Must have a valid host
    if not parsed_url.netloc:
        logger.warning(f"Invalid image URL - no host: {image_url}")
        return Response(status_code=404, content=b"", media_type="image/png")
    
    # Check if domain is allowed
    host = parsed_url.netloc.lower()
    is_allowed = any(
        host == domain or host.endswith(f".{domain}")
        for domain in ALLOWED_IMAGE_DOMAINS
    )
    
    if not is_allowed:
        logger.warning(f"Cover art from untrusted domain blocked: {host}")
        return Response(status_code=404, content=b"", media_type="image/png")
    
    # Proxy the image instead of redirecting (eliminates Open Redirect risk)
    # Also provides caching opportunity and hides external URLs from client
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                image_url,
                follow_redirects=True,
                headers={"User-Agent": "Audiovault/1.0"}
            )
            
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch cover art: {resp.status_code}")
                return Response(status_code=404, content=b"", media_type="image/png")
            
            # Detect content type
            content_type = resp.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                }
            )
    except httpx.RequestError as e:
        logger.warning(f"Error fetching cover art: {e}")
        return Response(status_code=404, content=b"", media_type="image/png")


@router.get("/hls.view")
async def hls_stream(
    id: str = Query(..., description="Song ID"),
    bitRate: str = Query(None, description="Bitrate list"),
    current_user: User = Depends(subsonic_auth),
):
    """
    HLS streaming (not implemented).
    
    Returns error - use regular stream instead.
    """
    return subsonic_error(0, "HLS streaming not supported. Use stream.view instead.")
