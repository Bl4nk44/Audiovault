from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RecommendedTrack(BaseModel):
    name: str
    artist: str
    url: str
    image_url: Optional[str] = None
    mbid: Optional[str] = None
    score: float = 0.0
    match: float = 0.0
    playcount: int = 0
    reason: Optional[str] = None


class RecommendedArtist(BaseModel):
    name: str
    url: str
    image_url: Optional[str] = None
    mbid: Optional[str] = None
    match: float = 0.0
    tags: List[str] = []


class RecommendedPlaylist(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    track_count: int = 0
    source: str = "spotify"
    url: Optional[str] = None


class RecommendationResponse(BaseModel):
    tracks: List[RecommendedTrack] = []
    artists: List[RecommendedArtist] = []
    playlists: List[RecommendedPlaylist] = []
    source: str
    cache_status: str = "miss"
    lastfm_connected: bool = False
    generated_at: datetime = datetime.now()
