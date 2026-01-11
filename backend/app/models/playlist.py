from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, index=True, nullable=False)
    comment = Column(String, nullable=True)
    owner_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="playlists")
    tracks = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.order",
    )


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    playlist_id = Column(Uuid(as_uuid=True), ForeignKey("playlists.id"), primary_key=True)
    track_id = Column(Uuid(as_uuid=True), ForeignKey("tracks.id"), primary_key=True)
    order = Column(Integer, nullable=False, default=0)

    # Relationships
    playlist = relationship("Playlist", back_populates="tracks")
    track = relationship("Track")
