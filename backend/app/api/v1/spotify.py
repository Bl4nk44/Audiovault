from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.spotify_service import SpotifyService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

SPOTIFY_NOT_CONFIGURED_MSG = "Spotify service not configured"


@router.get("/search")
async def search_spotify(
    q: str,
    limit: int = 20,
    offset: int = 0,
    type: str = "track",
    current_user: User = Depends(get_current_active_user),
):
    import logging

    logger = logging.getLogger(__name__)

    service = SpotifyService()

    try:
        return await service.search(q, limit, offset, type)
    except Exception as e:
        logger.error(f"Error in spotify search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/track/{track_id}")
async def get_spotify_track(track_id: str, current_user: User = Depends(get_current_active_user)):
    service = SpotifyService()

    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.get("/playlist/{playlist_id}")
async def get_spotify_playlist(playlist_id: str, current_user: User = Depends(get_current_active_user)):
    service = SpotifyService()

    playlist = await service.get_playlist_details(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return playlist


@router.get("/artist/{artist_id}")
async def get_spotify_artist(artist_id: str, current_user: User = Depends(get_current_active_user)):
    service = SpotifyService()

    artist = await service.get_artist_details(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    return artist


@router.get("/album/{album_id}")
async def get_spotify_album(album_id: str, current_user: User = Depends(get_current_active_user)):
    """Get album details with all tracks."""
    service = SpotifyService()

    album = await service.get_album_details(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return album
