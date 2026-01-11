from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ArtistBase(BaseModel):
    name: str
    bio: str | None = None
    spotify_id: str | None = None
    deezer_id: str | None = None
    images: dict[str, Any] | None = {}


class ArtistCreate(ArtistBase):
    pass


class ArtistResponse(ArtistBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AlbumBase(BaseModel):
    title: str
    release_date: datetime | None = None
    images: dict[str, Any] | None = {}


class AlbumResponse(AlbumBase):
    id: UUID
    artist_id: UUID

    class Config:
        from_attributes = True
