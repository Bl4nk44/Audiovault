from uuid import UUID

from pydantic import BaseModel


class DownloadCreate(BaseModel):
    track_id: UUID
    source: str
    playlist_name: str | None = None
