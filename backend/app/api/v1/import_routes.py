from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.providers import provider_manager
from app.schemas.metadata import PlaylistMetadata
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ImportRequest(BaseModel):
    url: str

@router.post("/playlist", response_model=PlaylistMetadata)
async def import_playlist(request: ImportRequest):
    """
    Import a playlist from a URL (Tidal, SoundCloud, Apple Music, etc.)
    using the Universal Provider system.
    Returns the extracted metadata for preview.
    """
    logger.info(f"Importing playlist from URL: {request.url}")
    
    try:
        playlist = await provider_manager.extract_playlist(request.url)
        if not playlist:
            raise HTTPException(status_code=404, detail="Could not extract playlist. Provider returned no data.")
            
        logger.info(f"Extracted {len(playlist.tracks)} tracks from {playlist.title}")
        return playlist
        
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
