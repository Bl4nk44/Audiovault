import logging
from datetime import UTC, datetime
from typing import Annotated

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.lastfm import NowPlayingRequest, ScrobbleRequest
from app.schemas.recommendation import RecommendationResponse
from app.services.lastfm_service import LastfmError, LastfmService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


def get_lastfm_service() -> LastfmService:
    return LastfmService()


@router.get("/connect")
async def connect_lastfm(
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Generate Last.fm auth URL.
    User should be redirected here.
    """
    return {"auth_url": service.get_auth_url()}


@router.get("/callback")
async def lastfm_callback(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Exchange token for session key and save to user profile.
    """
    try:
        session_data = await service.get_session(token)
        username = session_data.get("name")
        key = session_data.get("key")

        if not key:
            raise HTTPException(status_code=400, detail="No session key received from Last.fm")

        # Update user
        current_user.lastfm_session_key = key
        current_user.lastfm_username = username
        current_user.lastfm_connected_at = datetime.now(UTC)

        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

        return {"status": "connected", "username": username}

    except LastfmError as e:
        raise HTTPException(status_code=400, detail=f"Last.fm authentication failed: {str(e)}")


@router.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
    force_refresh: bool = False,
    source: str = "auto",
):
    """
    Get personalized recommendations.
    Source: 'auto'.
    """
    # Initialize engine with service
    from app.services.recommendation_engine import HybridRecommendationEngine

    engine = HybridRecommendationEngine(service)

    return await engine.get_recommendations(user=current_user, source=source, force_refresh=force_refresh)


@router.post("/scrobble/now_playing")
async def update_now_playing(
    request: NowPlayingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
):
    """Update Now Playing status."""
    from app.services.scrobbler import AudiovaultScrobbler

    scrobbler = AudiovaultScrobbler(service)

    await scrobbler.update_now_playing(current_user, request.track, request.artist, request.album)
    return {"status": "ok"}


@router.post("/scrobble")
async def scrobble_track(
    request: ScrobbleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
):
    """Scrobble a track."""
    from app.services.scrobbler import AudiovaultScrobbler

    scrobbler = AudiovaultScrobbler(service)

    success = await scrobbler.scrobble_track(
        current_user, request.track, request.artist, request.timestamp, request.album
    )
    if not success:
        # We don't raise 400 because scrobbling is "best effort" usually,
        # but returning status let client know.
        return {"status": "ignored_or_failed"}

    return {"status": "scrobbled"}


@router.post("/disconnect")
async def disconnect_lastfm(
    db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]
):
    """Remove Last.fm connection."""
    current_user.lastfm_session_key = None
    current_user.lastfm_username = None
    current_user.lastfm_connected_at = None

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return {"status": "disconnected"}


@router.get("/status")
async def lastfm_status(current_user: Annotated[User, Depends(get_current_user)]):
    """Check connection status."""
    return {"connected": current_user.lastfm_session_key is not None, "username": current_user.lastfm_username}


@router.get("/profile")
async def get_lastfm_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LastfmService, Depends(get_lastfm_service)],
):
    """Get Last.fm user profile info and friends."""
    if not current_user.lastfm_username:
        raise HTTPException(status_code=400, detail="Last.fm not connected")

    username = current_user.lastfm_username

    try:
        # Fetch user info and friends in parallel, ensuring one failure doesn't break everything
        import asyncio

        results = await asyncio.gather(
            service.get_user_info(username), service.get_user_friends(username, limit=8), return_exceptions=True
        )

        user_info_result, friends_result = results

        # If fetching user info failed, we can't show the profile
        if isinstance(user_info_result, Exception):
            logger.error(f"Failed to fetch user info for {username}: {user_info_result}")
            raise user_info_result

        # If fetching friends failed, just show empty list (graceful degradation)
        friends = []
        if isinstance(friends_result, Exception):
            logger.warning(f"Failed to fetch friends for {username}: {friends_result}")
        else:
            friends = friends_result

        return {"user": user_info_result, "friends": friends}
    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        # If it was the user_info error re-raised above, it will be caught here
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")
