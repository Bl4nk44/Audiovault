from typing import Annotated

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.deezer_service import DeezerService
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/search")
async def search_deezer(
    q: str,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    service = DeezerService()
    return await service.search(q, limit, offset)


@router.get("/playlist/{playlist_id}", responses={404: {"description": "Not found"}})
async def get_deezer_playlist(playlist_id: str, current_user: Annotated[User, Depends(get_current_active_user)] = ...):
    service = DeezerService()
    from fastapi import HTTPException

    playlist = await service.get_playlist_details(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.get("/artist/{artist_id}", responses={404: {"description": "Not found"}})
async def get_deezer_artist(artist_id: str, current_user: Annotated[User, Depends(get_current_active_user)] = ...):
    service = DeezerService()
    from fastapi import HTTPException

    artist = await service.get_artist_details(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist
