from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.apple_music_service import apple_music_service

router = APIRouter()


@router.get("/search")
async def search_apple_music(
    q: str,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    # An Apple Music URL → extract that album/playlist/track via yt-dlp.
    if apple_music_service.can_handle(q):
        # Check if it looks like a playlist/album URL that we should return as a container
        if "/playlist/" in q or "/album/" in q:
            playlist_info = await apple_music_service.get_playlist_info(q)
            if playlist_info:
                return [playlist_info]

        # Fallback to returning tracks
        return await apple_music_service.get_tracks(q)

    # A free-text phrase → keyword search via the public iTunes Search API.
    return await apple_music_service.search(q, limit)
