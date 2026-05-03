from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.album import Album
    from app.models.artist import Artist
    from app.models.download import Download
    from app.models.watchlist_item import WatchlistItem


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    artist: Mapped[str | None] = mapped_column(
        String(500), index=True, nullable=True
    )  # Kept for simple search/display, nullable if using rel
    album: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Kept for simple search/display

    # Foreign Keys
    artist_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("artists.id"), nullable=True)
    album_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("albums.id"), nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer)  # milliseconds

    # Service IDs (for cross-platform lookup)
    isrc: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    spotify_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    youtube_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    deezer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    musicbrainz_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    soundcloud_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Metadata provenance
    metadata_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'spotify', 'deezer', 'musicbrainz'
    metadata_confidence: Mapped[float | None] = mapped_column(default=1.0)  # 0.0-1.0

    # Metadata
    metadata_content: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        default={
            "image_url": None,
            "album_art": None,
            "genre": None,
            "year": None,
            "popularity": 0,
        },
    )

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))

    # Relationships
    downloads: Mapped[list[Download]] = relationship("Download", back_populates="track")
    artist_rel: Mapped[Artist] = relationship("Artist", back_populates="tracks")
    album_rel: Mapped[Album] = relationship("Album", back_populates="tracks")
    watchlist_items: Mapped[list[WatchlistItem]] = relationship("WatchlistItem", back_populates="track")
