from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.soundcloud_service import soundcloud_service

router = APIRouter()


@router.get("/search")
async def search_soundcloud(
    q: str,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    # A SoundCloud URL → extract that track/playlist directly.
    if soundcloud_service.can_handle(q):
        if "/sets/" in q:
            playlist_info = await soundcloud_service.get_playlist_info(q)
            if playlist_info:
                return [playlist_info]

        return await soundcloud_service.get_tracks(q)

    # A free-text phrase → keyword search via yt-dlp scsearch.
    return await soundcloud_service.search(q, limit)
