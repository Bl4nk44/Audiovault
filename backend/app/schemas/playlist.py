from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlaylistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    comment: str | None = None
    public: bool = False


class PlaylistCreate(PlaylistBase):
    pass


class PlaylistUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    comment: str | None = None
    public: bool | None = None


class PlaylistTrackAdd(BaseModel):
    track_ids: list[UUID]


class PlaylistTrackResponse(BaseModel):
    track_id: UUID
    order: int
    title: str
    artist: str
    album: str | None
    duration_ms: int
    image_url: str | None

    class Config:
        from_attributes = True


class PlaylistResponse(PlaylistBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    tracks_count: int = 0
    tracks: list[PlaylistTrackResponse] = []

    class Config:
        from_attributes = True
