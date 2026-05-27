import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.spotify_service import SpotifyService, spotify_service

router = APIRouter()
logger = logging.getLogger(__name__)

SpotifyDep = Annotated[SpotifyService, Depends(lambda: spotify_service)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


class TokenInject(BaseModel):
    access_token: str
    expires_in: int = 3600


@router.get("/oauth/start", summary="Start Spotify OAuth — redirects browser to Spotify login")
async def spotify_oauth_start(
    spotify: SpotifyDep,
):
    """
    Open this URL directly in the browser — no token needed.
    Spotify will redirect back to http://127.0.0.1:9900/ after login.
    The refresh token is saved automatically — you only need to do this once.
    """
    url = spotify.get_auth_url()
    return RedirectResponse(
        url
    )  # deepcode ignore OR: URL is built internally by get_auth_url(), not from request params


@router.get("/oauth/status", summary="Check whether OAuth user-auth is active")
async def spotify_oauth_status(
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    has_token = bool(spotify._token and time.time() < spotify._token_expires_at)
    remaining = max(0, int(spotify._token_expires_at - time.time())) if has_token else 0
    return {
        "oauth_authenticated": spotify.is_oauth_authenticated,
        "has_active_token": has_token,
        "expires_in_seconds": remaining,
    }


@router.post("/inject-token", summary="Inject a Spotify Bearer token obtained from the browser")
async def inject_spotify_token(
    body: TokenInject,
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    """
    Fallback: manually paste a Bearer token copied from DevTools.
    Prefer /oauth/start for persistent auth that survives restarts.
    """
    spotify.inject_token(body.access_token, body.expires_in)
    return {"status": "ok", "expires_in_seconds": body.expires_in}


@router.get("/token-status", summary="Check whether a valid Spotify token is cached")
async def spotify_token_status(
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    has_token = bool(spotify._token and time.time() < spotify._token_expires_at)
    remaining = max(0, int(spotify._token_expires_at - time.time())) if has_token else 0
    return {"has_token": has_token, "expires_in_seconds": remaining}


@router.get("/search", responses={500: {"description": "Internal server error"}})
async def search_spotify(
    q: str,
    limit: int = 20,
    offset: int = 0,
    type: str = "track",
    current_user: CurrentUser = ...,
    spotify: SpotifyDep = ...,
):
    try:
        return await spotify.search(q, limit, offset, type)
    except Exception as e:
        logger.error(f"Spotify search error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/track/{track_id}", responses={404: {"description": "Not found"}})
async def get_spotify_track(
    track_id: str,
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    track = await spotify.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.get("/playlist/{playlist_id}", responses={404: {"description": "Not found"}})
async def get_spotify_playlist(
    playlist_id: str,
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    playlist = await spotify.get_playlist_details(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.get("/artist/{artist_id}", responses={404: {"description": "Not found"}})
async def get_spotify_artist(
    artist_id: str,
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    artist = await spotify.get_artist_details(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist


@router.get("/album/{album_id}", responses={404: {"description": "Not found"}})
async def get_spotify_album(
    album_id: str,
    current_user: CurrentUser,
    spotify: SpotifyDep,
):
    album = await spotify.get_album_details(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album
