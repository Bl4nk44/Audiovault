from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.metadata_service import MetadataService
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from typing import Any
from pydantic import BaseModel

class FetchMetadataRequest(BaseModel):
    source: str
    id: str # External ID (e.g. Spotify ID)

router = APIRouter()

@router.get("/{track_id}")
async def get_track_metadata(
    track_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Pobierz szczegółowe metadane dla utworu.
    """
    service = MetadataService(db)
    metadata = await service.get_track_metadata(track_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Track not found")
        
    return metadata
    return metadata

@router.post("/fetch")
async def fetch_metadata(
    request: FetchMetadataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Pobierz metadane z zewnętrznego serwisu i zapisz w bazie (Track/Artist/Album).
    Zwraca obiekt Track, w tym jego UUID (id) potrzebne do zlecenia pobierania.
    """
    service = MetadataService(db)
    track = await service.fetch_and_save_track_metadata(request.source, request.id)
    
    if not track:
        raise HTTPException(status_code=404, detail="Could not fetch metadata")
        
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "image_url": track.metadata_content.get("image_url") if track.metadata_content else None
    }
