from fastapi import APIRouter
from app.api.v1 import auth, spotify, downloads, settings, watchlist, history, youtube, dashboard, stream

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(spotify.router, prefix="/spotify", tags=["spotify"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
