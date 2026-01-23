from datetime import UTC, datetime
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artist import Artist
    from app.models.track import Track


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    release_date: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Full date or just year
    total_tracks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    artist_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("artists.id"), nullable=True)

    # External IDs
    spotify_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    deezer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Images (cover art)
    images: Mapped[dict | None] = mapped_column(JSON, default={})

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))

    # Relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="albums")
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="album_rel")
