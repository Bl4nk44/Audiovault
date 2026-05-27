from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.amazon_music_service import amazon_music_service

router = APIRouter()


@router.get("/search")
async def search_amazon_music(
    q: str,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    # Amazon Music Service currently only supports URL extraction via yt-dlp
    if amazon_music_service.can_handle(q):
        if "/playlists/" in q or "/albums/" in q:
            playlist_info = await amazon_music_service.get_playlist_info(q)
            if playlist_info:
                return [playlist_info]

        return await amazon_music_service.get_tracks(q)
    return []
