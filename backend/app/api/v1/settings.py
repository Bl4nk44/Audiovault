from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.credentials import ServiceCredentials
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class SettingsUpdate(BaseModel):
    spotifyClientId: Optional[str] = None
    spotifyClientSecret: Optional[str] = None
    youtubeApiKey: Optional[str] = None
    downloadPath: Optional[str] = None
    maxParallelDownloads: Optional[int] = None

@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Get credentials
    stmt = select(ServiceCredentials).where(ServiceCredentials.user_id == current_user.id)
    result = await db.execute(stmt)
    credentials = result.scalars().all()
    
    creds_map = {c.service: c for c in credentials}
    
    spotify_creds = creds_map.get('spotify')
    youtube_creds = creds_map.get('youtube')
    
    return {
        "spotifyClientId": spotify_creds.extra_data.get('client_id', '') if spotify_creds else '',
        "spotifyClientSecret": spotify_creds.extra_data.get('client_secret', '') if spotify_creds else '',
        "youtubeApiKey": youtube_creds.extra_data.get('api_key', '') if youtube_creds else '',
        "downloadPath": current_user.preferences.get('download_path', '/downloads'),
        "maxParallelDownloads": current_user.preferences.get('max_parallel_downloads', 3)
    }

@router.post("/")
async def update_settings(
    settings: SettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Update User Preferences
    current_prefs = dict(current_user.preferences) if current_user.preferences else {}
    if settings.downloadPath:
        current_prefs['download_path'] = settings.downloadPath
    if settings.maxParallelDownloads:
        current_prefs['max_parallel_downloads'] = settings.maxParallelDownloads
    
    current_user.preferences = current_prefs
    
    # Update Spotify Credentials
    if settings.spotifyClientId or settings.spotifyClientSecret:
        stmt = select(ServiceCredentials).where(
            ServiceCredentials.user_id == current_user.id,
            ServiceCredentials.service == 'spotify'
        )
        result = await db.execute(stmt)
        spotify_creds = result.scalars().first()
        
        if not spotify_creds:
            spotify_creds = ServiceCredentials(
                user_id=current_user.id,
                service='spotify',
                extra_data={}
            )
            db.add(spotify_creds)
        
        extra_data = dict(spotify_creds.extra_data) if spotify_creds.extra_data else {}
        if settings.spotifyClientId:
            extra_data['client_id'] = settings.spotifyClientId
        if settings.spotifyClientSecret:
            extra_data['client_secret'] = settings.spotifyClientSecret
        spotify_creds.extra_data = extra_data

    # Update YouTube Credentials
    if settings.youtubeApiKey:
        stmt = select(ServiceCredentials).where(
            ServiceCredentials.user_id == current_user.id,
            ServiceCredentials.service == 'youtube'
        )
        result = await db.execute(stmt)
        youtube_creds = result.scalars().first()
        
        if not youtube_creds:
            youtube_creds = ServiceCredentials(
                user_id=current_user.id,
                service='youtube',
                extra_data={}
            )
            db.add(youtube_creds)
            
        extra_data = dict(youtube_creds.extra_data) if youtube_creds.extra_data else {}
        extra_data['api_key'] = settings.youtubeApiKey
        youtube_creds.extra_data = extra_data

    await db.commit()
    return {"status": "success"}
