from pydantic import BaseModel


class NowPlayingRequest(BaseModel):
    track: str
    artist: str
    album: str | None = None


class ScrobbleRequest(BaseModel):
    track: str
    artist: str
    timestamp: int | None = None
    album: str | None = None
