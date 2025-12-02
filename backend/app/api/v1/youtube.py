from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.youtube_service import YouTubeService
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/search")
async def search_youtube(
    q: str, 
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    # YouTube Music API doesn't support simple offset pagination for search
    # So we only return results for the first page to avoid duplicates
    if offset > 0:
        return []
        
    service = YouTubeService()
    return service.search(q, limit)
