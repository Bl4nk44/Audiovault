from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ArtistMetadata(BaseModel):
    name: str
    id: Optional[str] = None
    url: Optional[str] = None

class AlbumMetadata(BaseModel):
    title: str
    artist: str
    year: Optional[int] = None
    cover_url: Optional[str] = None

class TrackMetadata(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    isrc: Optional[str] = None
    source: Optional[str] = None
    
class PlaylistMetadata(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    tracks: List[TrackMetadata] = []
