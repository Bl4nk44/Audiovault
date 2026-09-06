"""Provider-agnostic listening-service API — connect / disconnect / status /
profile / scrobble for any listening provider (Last.fm, ListenBrainz).

The older ``/api/v1/lastfm/*`` routes stay for backwards compatibility; new
clients use these.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.lastfm import NowPlayingRequest, ScrobbleRequest
from app.services.credentials_service import credentials_service
from app.services.lastfm_service import LastfmService
from app.services.listening.base import ListeningError
from app.services.listening.registry import PROVIDERS, connected_providers, get_provider
from app.services.scrobbler import AudiovaultScrobbler

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_PREFERENCES = {"auto", *PROVIDERS.keys()}


class ConnectTokenRequest(BaseModel):
    token: str


class PreferenceRequest(BaseModel):
    listening_provider: str


async def _connected_map(user: User, db: AsyncSession) -> dict[str, str]:
    """provider name -> connected username."""
    return {prov.name: creds.username for prov, creds in await connected_providers(user, db)}


@router.get("/providers")
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    connected = await _connected_map(current_user, db)
    preference = (current_user.preferences or {}).get("listening_provider", "auto")
    return {
        "preference": preference,
        "providers": [
            {
                "name": p.name,
                "display_name": p.display_name,
                "connected": p.name in connected,
                "username": connected.get(p.name),
                "supports_recommendations": p.supports_recommendations,
                "connects_with_token": p.connects_with_token,
            }
            for p in PROVIDERS.values()
        ],
    }


@router.post("/connect/{provider}", responses={400: {"description": "Bad request"}})
async def connect_provider(
    provider: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    body: ConnectTokenRequest | None = None,
):
    """Token-paste providers (ListenBrainz): validate ``body.token`` and store it.

    Redirect providers (Last.fm): return ``auth_url`` for the browser to visit;
    the token comes back via ``GET /api/v1/lastfm/callback``.
    """
    prov = get_provider(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")

    if not prov.connects_with_token:
        # Last.fm redirect flow.
        origin = request.headers.get("origin") or request.headers.get("referer")
        base_url = None
        if origin:
            from urllib.parse import urlparse

            parsed = urlparse(origin)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        return {"auth_url": LastfmService().get_auth_url(base_url=base_url)}

    if body is None or not body.token.strip():
        raise HTTPException(status_code=400, detail="token is required")

    try:
        identity = await prov.validate_credentials(body.token)
    except ListeningError as e:
        raise HTTPException(status_code=400, detail=f"{prov.display_name} authentication failed: {e}") from e

    await credentials_service.store_tokens(
        db,
        current_user.id,
        prov.name,
        access_token=body.token.strip(),
        extra_data={"username": identity.username, "connected_at": datetime.now(UTC).isoformat()},
    )
    return {"status": "connected", "provider": prov.name, "username": identity.username}


@router.post("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    prov = get_provider(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")

    if prov.name == "lastfm":
        current_user.lastfm_session_key = None
        current_user.lastfm_username = None
        current_user.lastfm_connected_at = None
        db.add(current_user)
        await db.commit()
    else:
        await credentials_service.delete_credentials(db, current_user.id, prov.name)
    return {"status": "disconnected", "provider": prov.name}


@router.put("/preference")
async def set_preference(
    body: PreferenceRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if body.listening_provider not in VALID_PREFERENCES:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{body.listening_provider}'")
    prefs = dict(current_user.preferences or {})
    prefs["listening_provider"] = body.listening_provider
    current_user.preferences = prefs
    db.add(current_user)
    await db.commit()
    return {"status": "ok", "listening_provider": body.listening_provider}


@router.get("/profile/{provider}", responses={400: {"description": "Bad request"}})
async def provider_profile(
    provider: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    prov = get_provider(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")
    creds = await prov.get_credentials(current_user, db)
    if creds is None:
        raise HTTPException(status_code=400, detail=f"{prov.display_name} not connected")
    try:
        return await prov.get_profile(creds)
    except ListeningError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {e}") from e


@router.post("/scrobble")
async def scrobble(
    body: ScrobbleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    scrobbler = await AudiovaultScrobbler.for_user(current_user, db)
    ok = await scrobbler.scrobble_track(current_user, body.track, body.artist, body.timestamp, body.album)
    return {"status": "scrobbled" if ok else "ignored_or_failed"}


@router.post("/scrobble/now_playing")
async def now_playing(
    body: NowPlayingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    scrobbler = await AudiovaultScrobbler.for_user(current_user, db)
    await scrobbler.update_now_playing(current_user, body.track, body.artist, body.album)
    return {"status": "ok"}
