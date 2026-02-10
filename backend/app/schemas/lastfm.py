from typing import Optional

from pydantic import BaseModel


class NowPlayingRequest(BaseModel):
    track: str
    artist: str
    album: Optional[str] = None


class ScrobbleRequest(BaseModel):
    track: str
    artist: str
    timestamp: Optional[int] = None
    album: Optional[str] = None
