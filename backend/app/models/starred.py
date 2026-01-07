from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.base import Base


class StarredArtist(Base):
    __tablename__ = "starred_artists"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    artist_id = Column(
        Uuid(as_uuid=True), ForeignKey("artists.id"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="starred_artists")
    artist = relationship("Artist")

    __table_args__ = (
        UniqueConstraint("user_id", "artist_id", name="unique_starred_artist"),
    )


class StarredAlbum(Base):
    __tablename__ = "starred_albums"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    album_id = Column(
        Uuid(as_uuid=True), ForeignKey("albums.id"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="starred_albums")
    album = relationship("Album")

    __table_args__ = (
        UniqueConstraint("user_id", "album_id", name="unique_starred_album"),
    )


class StarredTrack(Base):
    __tablename__ = "starred_tracks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    track_id = Column(
        Uuid(as_uuid=True), ForeignKey("tracks.id"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="starred_tracks")
    track = relationship("Track")

    __table_args__ = (
        UniqueConstraint("user_id", "track_id", name="unique_starred_track"),
    )
