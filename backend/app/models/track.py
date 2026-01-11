from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), index=True, nullable=False)
    artist = Column(String(500), index=True, nullable=True)  # Kept for simple search/display, nullable if using rel
    album = Column(String(500), nullable=True)  # Kept for simple search/display

    # Foreign Keys
    artist_id = Column(Uuid(as_uuid=True), ForeignKey("artists.id"), nullable=True)
    album_id = Column(Uuid(as_uuid=True), ForeignKey("albums.id"), nullable=True)

    duration_ms = Column(Integer)  # milliseconds

    # Service IDs (for cross-platform lookup)
    isrc = Column(String(20), unique=True, nullable=True)
    spotify_id = Column(String(100), nullable=True, unique=True)
    youtube_id = Column(String(100), nullable=True, unique=True)
    deezer_id = Column(String(100), nullable=True, unique=True)

    # Metadata
    metadata_content = Column(
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

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))

    # Relationships
    downloads = relationship("Download", back_populates="track")
    artist_rel = relationship("Artist", back_populates="tracks")
    album_rel = relationship("Album", back_populates="tracks")
    watchlist_items = relationship("WatchlistItem", back_populates="track")
