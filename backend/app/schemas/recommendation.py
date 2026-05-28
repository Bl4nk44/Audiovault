from datetime import datetime

from pydantic import BaseModel, Field


class RecommendedTrack(BaseModel):
    name: str
    artist: str
    url: str
    image_url: str | None = None
    mbid: str | None = None
    score: float = 0.0
    match: float = 0.0
    playcount: int = 0
    reason: str | None = None


class RecommendedArtist(BaseModel):
    name: str
    url: str
    image_url: str | None = None
    mbid: str | None = None
    match: float = 0.0
    rank: int | None = None
    tags: list[str] = []


class RecommendedPlaylist(BaseModel):
    id: str
    title: str
    description: str | None = None
    image_url: str | None = None
    track_count: int = 0
    source: str = "spotify"
    url: str | None = None


class RecommendationResponse(BaseModel):
    tracks: list[RecommendedTrack] = []
    artists: list[RecommendedArtist] = []
    playlists: list[RecommendedPlaylist] = []
    source: str
    cache_status: str = "miss"
    lastfm_connected: bool = False
    generated_at: datetime = Field(default_factory=datetime.now)
