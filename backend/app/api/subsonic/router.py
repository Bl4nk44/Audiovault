"""
Main Subsonic API router.

Mounts all Subsonic API handlers under /rest prefix.
"""

from app.api.subsonic.handlers import (
    system, # Contains ping, getLicense, getToken
    browse, 
    search,
    media,
    playlist,
    user,
    lists,
    lyrics
)
from fastapi import APIRouter

# Create main router
router = APIRouter(prefix="/rest", tags=["subsonic"])

# Include all handler routers
router.include_router(system.router)
router.include_router(browse.router)
router.include_router(search.router)
router.include_router(media.router)
router.include_router(playlist.router)
router.include_router(user.router)
router.include_router(lists.router)
router.include_router(lyrics.router)
