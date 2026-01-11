from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.youtube_service import YouTubeService
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/search")
async def search_youtube(
    q: str,
    limit: int = 20,
    offset: int = 0,
    type: str = "song",
    current_user: User = Depends(get_current_active_user),
):
    # YouTube Music API doesn't support simple offset pagination for search
    # So we only return results for the first page to avoid duplicates
    if offset > 0:
        return []

    service = YouTubeService()
    return service.search(q, limit, type)


@router.get("/playlist/{playlist_id}")
async def get_youtube_playlist(playlist_id: str, current_user: User = Depends(get_current_active_user)):
    service = YouTubeService()
    playlist = service.get_playlist_details(playlist_id)

    if not playlist:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Playlist not found")

    return playlist
