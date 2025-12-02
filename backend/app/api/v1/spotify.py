from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.spotify_service import SpotifyService
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/search")
async def search_spotify(
    q: str, 
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    service = SpotifyService()
    if not service.client:
        raise HTTPException(status_code=503, detail="Spotify service not configured")
    
    return service.search(q, limit, offset)

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
