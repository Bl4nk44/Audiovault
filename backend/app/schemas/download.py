from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class DownloadCreate(BaseModel):
    track_id: UUID
    source: str
    playlist_name: Optional[str] = None
