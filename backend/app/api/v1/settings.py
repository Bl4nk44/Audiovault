from typing import Annotated

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.credentials import ServiceCredentials
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


class SettingsUpdate(BaseModel):
    spotifyClientId: str | None = None  # noqa: N815
    spotifyClientSecret: str | None = None  # noqa: N815
    youtubeApiKey: str | None = None  # noqa: N815
    downloadPath: str | None = None  # noqa: N815
    maxParallelDownloads: int | None = None  # noqa: N815
    theme: str | None = None
    language: str | None = None
    filenameSchema: str | None = None  # noqa: N815
    audioQuality: str | None = None  # noqa: N815


class VerifySpotify(BaseModel):
    clientId: str  # noqa: N815
    clientSecret: str  # noqa: N815


class VerifyYouTube(BaseModel):
    apiKey: str  # noqa: N815


@router.post("/verify/spotify", responses={400: {"description": "Bad request"}})
async def verify_spotify(creds: VerifySpotify):
    import asyncio

    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    def _check_spotify():
        client = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(client_id=creds.clientId, client_secret=creds.clientSecret)
        )
        client.search(q="test", limit=1)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _check_spotify)
        return {"status": "valid"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/verify/youtube", responses={400: {"description": "Bad request"}})
async def verify_youtube(creds: VerifyYouTube):
    import httpx

    try:
        # Simple test request to YouTube Data API
        url = "https://www.googleapis.com/youtube/v3/search"
        async with httpx.AsyncClient() as client:
            response = await client.get(  # nosemgrep: python.fastapi.net.tainted-fastapi-http-request-httpx.tainted-fastapi-http-request-httpx  # noqa: E501
                url, params={"part": "snippet", "q": "test", "key": creds.apiKey, "maxResults": "1"}
            )

        if response.status_code == 200:
            return {"status": "valid"}
        else:
            raise HTTPException(status_code=400, detail="Invalid API Key")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/")
async def get_settings(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    # Get credentials
    stmt = select(ServiceCredentials).where(ServiceCredentials.user_id == current_user.id)
    result = await db.execute(stmt)
    credentials = result.scalars().all()

    creds_map = {c.service: c for c in credentials}

    spotify_creds = creds_map.get("spotify")
    youtube_creds = creds_map.get("youtube")

    return {
        "spotifyClientId": (spotify_creds.extra_data or {}).get("client_id", "") if spotify_creds else "",
        "spotifyClientSecret": (spotify_creds.extra_data or {}).get("client_secret", "") if spotify_creds else "",
        "youtubeApiKey": (youtube_creds.extra_data or {}).get("api_key", "") if youtube_creds else "",
        "downloadPath": (current_user.preferences or {}).get("download_path", "/downloads"),
        "maxParallelDownloads": (current_user.preferences or {}).get("max_parallel_downloads", 3),
        "theme": (current_user.preferences or {}).get("theme", "dark"),
        "language": (current_user.preferences or {}).get("language", "en"),
        "filenameSchema": (current_user.preferences or {}).get("filename_schema", "{artist} - {title}"),
        "audioQuality": (current_user.preferences or {}).get("audio_quality", "high"),
    }


@router.post("/")
async def update_settings(
    settings: SettingsUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _update_user_preferences(current_user, settings)

    await _update_service_credentials(
        db,
        current_user,
        "spotify",
        {
            "client_id": settings.spotifyClientId,
            "client_secret": settings.spotifyClientSecret,
        },
    )

    await _update_service_credentials(db, current_user, "youtube", {"api_key": settings.youtubeApiKey})

    await db.commit()
    return {"status": "success"}


def _update_user_preferences(user: User, settings: SettingsUpdate):
    current_prefs = dict(user.preferences) if user.preferences else {}
    mapping = {
        "download_path": settings.downloadPath,
        "max_parallel_downloads": settings.maxParallelDownloads,
        "theme": settings.theme,
        "language": settings.language,
        "filename_schema": settings.filenameSchema,
        "audio_quality": settings.audioQuality,
    }

    updated = False
    for key, value in mapping.items():
        if value is not None:
            current_prefs[key] = value
            updated = True

    if updated:
        user.preferences = current_prefs


async def _update_service_credentials(db: AsyncSession, user: User, service: str, updates: dict):
    # Filter out None values
    valid_updates = {k: v for k, v in updates.items() if v is not None}
    if not valid_updates:
        return

    stmt = select(ServiceCredentials).where(
        ServiceCredentials.user_id == user.id, ServiceCredentials.service == service
    )
    result = await db.execute(stmt)
    creds = result.scalars().first()

    if not creds:
        creds = ServiceCredentials(user_id=user.id, service=service, extra_data={})
        db.add(creds)

    extra_data = dict(creds.extra_data) if creds.extra_data else {}
    extra_data.update(valid_updates)
    creds.extra_data = extra_data
