import asyncio
import logging

import aiohttp
import yt_dlp
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from app.db.database import get_db
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.track import Track
from app.models.download import Download
from app.models.album import Album
import os

router = APIRouter()
logger = logging.getLogger(__name__)



@router.get("/{track_id}/cover")
async def get_track_cover(track_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get cover art for a track using native ID.
    Falls back to: DB -> Local File (cover.jpg) -> Embedded Art
    """
    # 1. Try to find track content
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()

    if not track:
        # Try finding by download if track_id is actually download_id (common confusion)
        result = await db.execute(select(Download).where(Download.id == track_id))
        download = result.scalar_one_or_none()
        if download and download.track:
            track = download.track
        else:
            raise HTTPException(status_code=404, detail="Track not found")

    # 2. Check metadata URL first
    # image_url = None
    # if track.metadata_content:
    #    image_url = track.metadata_content.get("image_url") or track.metadata_content.get("album_art")
    # If we have a remote URL, we could redirect, but for "native" feel lets try to serve local first

    # 3. Resolve local file path
    file_path = None
    
    # Try via Download entry first (most reliable for file path)
    dl_res = await db.execute(select(Download).where(Download.track_id == track.id))
    download = dl_res.scalars().first()
    
    if download and download.file_path and os.path.exists(download.file_path):
        file_path = download.file_path
    
    if not file_path:
        # 404 if no file source
        # Return generic placeholder or 404? 
        # Web app handles 404 by showing icon, so 404 is fine.
        raise HTTPException(status_code=404, detail="No media file found")

    directory = os.path.dirname(file_path)

    # 4. Check for local cover files
    cover_names = ["cover.jpg", "folder.jpg", "cover.png", "folder.png", "artwork.jpg", "artwork.png"]
    for name in cover_names:
        cover_path = os.path.join(directory, name)
        if os.path.exists(cover_path):
            with open(cover_path, "rb") as f:
                return Response(content=f.read(), media_type="image/jpeg" if name.endswith(".jpg") else "image/png")

    # 5. Extract embedded art
    try:
        import mutagen
        from mutagen.flac import Picture
        from mutagen.id3 import ID3, APIC

        audio = mutagen.File(file_path)
        
        if audio:
            # FLAC / Vorbis
            if hasattr(audio, "pictures") and audio.pictures:
                p = audio.pictures[0]
                return Response(content=p.data, media_type=p.mime)
            
            # ID3 (MP3)
            if hasattr(audio, "tags") and isinstance(audio.tags, ID3):
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        return Response(content=tag.data, media_type=tag.mime)
                        
            # MP4 / M4A
            if hasattr(audio, "tags") and "covr" in audio.tags:
                 covers = audio.tags["covr"]
                 if covers:
                     import mutagen.mp4
                     # MP4 covers are usually jpeg or png. content is bytes.
                     # atomicparsley says: data is jpeg if type 13, png if 14
                     # mutagen returns list of MP4Cover
                     c = covers[0]
                     mime = "image/jpeg" 
                     if c.imageformat == mutagen.mp4.MP4Cover.FORMAT_PNG:
                         mime = "image/png"
                     return Response(content=bytes(c), media_type=mime)

    except Exception as e:
        logger.error(f"Error extracting embedded art: {e}")

    # Fallback to Album art if linked
    if track.album_id:
        result = await db.execute(select(Album).where(Album.id == track.album_id))
        album = result.scalar_one_or_none()
        if album and album.images:
            # Here we might return a redirect to the external URL if it exists
            # This is a fallback if local extraction fails
            url = album.images.get("300") or album.images.get("640")
            if url:
                 return RedirectResponse(url)

    # If all fails
    raise HTTPException(status_code=404, detail="No cover art found")

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
        info = await loop.run_in_executor(stream_executor, lambda: ydl.extract_info(youtube_url, download=False))
        return info["url"], info.get("http_headers", {})


async def _stream_content(url: str, headers: dict = None):
    async with aiohttp.ClientSession() as session:
        # Pass headers to the request to avoid 403 Forbidden from strict servers (Youtube)
        async with session.get(url, headers=headers) as response:
            async for chunk in response.content.iter_chunked(8192):
                yield chunk
