from fastapi import APIRouter, Depends, HTTPException
from app.services.spotify_service import SpotifyService
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/search")
async def search_spotify(
    q: str, 
    limit: int = 20,
    offset: int = 0,
    type: str = 'track',
    current_user: User = Depends(get_current_active_user)
):
    import logging
    logger = logging.getLogger(__name__)
    
    service = SpotifyService()
    if not service.client:
        logger.error("Spotify service not configured")
        raise HTTPException(status_code=503, detail="Spotify service not configured")
    
    try:
        return service.search(q, limit, offset, type)
    except Exception as e:
        logger.error(f"Error in spotify search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/track/{track_id}")
async def get_spotify_track(
    track_id: str,
    current_user: User = Depends(get_current_active_user)
):
    service = SpotifyService()
    if not service.client:
        raise HTTPException(status_code=503, detail="Spotify service not configured")
        
    track = service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
        
    return track
