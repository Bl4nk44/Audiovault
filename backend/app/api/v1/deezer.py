from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.deezer_service import DeezerService
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/search")
async def search_deezer(
    q: str, 
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    service = DeezerService()
    return await service.search(q, limit, offset)
