from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.metadata_service import MetadataService
from app.core.dependencies import get_current_user
from typing import Any

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
