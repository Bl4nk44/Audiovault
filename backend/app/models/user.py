from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.base import Base
from app.models.download import Download

CASCADE_DELETE = "all, delete-orphan"


def default_preferences():
    return {
        "theme": "dark",
        "quality": "high",
        "auto_download": False,
        "language": "en",
        "filename_schema": "{user}/{service}/{playlist}/{artist} - {title}",
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    credentials = relationship(
        "ServiceCredentials", back_populates="user", cascade=CASCADE_DELETE
    )
    downloads = relationship(Download, back_populates="user", cascade=CASCADE_DELETE)
    playlists = relationship("Playlist", back_populates="owner", cascade=CASCADE_DELETE)
    watchlist = relationship("Watchlist", back_populates="user", cascade=CASCADE_DELETE)
    starred_artists = relationship(
        "StarredArtist", back_populates="user", cascade=CASCADE_DELETE
    )
    starred_albums = relationship(
        "StarredAlbum", back_populates="user", cascade=CASCADE_DELETE
    )
    starred_tracks = relationship(
        "StarredTrack", back_populates="user", cascade=CASCADE_DELETE
    )
    history = relationship(
        "ListeningHistory", back_populates="user", cascade=CASCADE_DELETE
    )

    # Preferences (JSONB)
    preferences = Column(JSON, default=default_preferences)
