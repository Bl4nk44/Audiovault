from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base

_USERS_FK = "users.id"
_ARTISTS_FK = "artists.id"
_ALBUMS_FK = "albums.id"
_TRACKS_FK = "tracks.id"


class StarredArtist(Base):
    __tablename__ = "starred_artists"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey(_USERS_FK), nullable=False, index=True)
    artist_id = Column(Uuid(as_uuid=True), ForeignKey(_ARTISTS_FK), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="starred_artists")
    artist = relationship("Artist")

    __table_args__ = (UniqueConstraint("user_id", "artist_id", name="unique_starred_artist"),)


class StarredAlbum(Base):
    __tablename__ = "starred_albums"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey(_USERS_FK), nullable=False, index=True)
    album_id = Column(Uuid(as_uuid=True), ForeignKey(_ALBUMS_FK), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="starred_albums")
    album = relationship("Album")

    __table_args__ = (UniqueConstraint("user_id", "album_id", name="unique_starred_album"),)


class StarredTrack(Base):
    __tablename__ = "starred_tracks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey(_USERS_FK), nullable=False, index=True)
    track_id = Column(Uuid(as_uuid=True), ForeignKey(_TRACKS_FK), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="starred_tracks")
    track = relationship("Track")

    __table_args__ = (UniqueConstraint("user_id", "track_id", name="unique_starred_track"),)
