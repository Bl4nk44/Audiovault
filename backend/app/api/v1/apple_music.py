from fastapi import APIRouter, Depends
from typing import List
from app.services.apple_music_service import apple_music_service
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/search")
async def search_apple_music(
    q: str, 
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    # Apple Music Service currently only supports URL extraction via yt-dlp
    if "music.apple.com" in q:
        # Check if it looks like a playlist/album URL that we should return as a container
        if "/playlist/" in q or "/album/" in q:
            playlist_info = await apple_music_service.get_playlist_info(q)
            if playlist_info:
                return [playlist_info]
        
        # Fallback to returning tracks
        return await apple_music_service.get_tracks(q)
    return []
