from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class ArtistBase(BaseModel):
    name: str
    bio: Optional[str] = None
    spotify_id: Optional[str] = None
    deezer_id: Optional[str] = None
    images: Optional[Dict[str, Any]] = {}

class ArtistCreate(ArtistBase):
    pass

class ArtistResponse(ArtistBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AlbumBase(BaseModel):
    title: str
    release_date: Optional[datetime] = None
    images: Optional[Dict[str, Any]] = {}

class AlbumResponse(AlbumBase):
    id: UUID
    artist_id: UUID

    class Config:
        from_attributes = True
