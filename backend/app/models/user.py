from datetime import UTC, datetime
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.download import Download

if TYPE_CHECKING:
    from app.models.playlist import Playlist
    from app.models.watchlist import Watchlist
    from app.models.credentials import ServiceCredentials
    from app.models.audit_log import AuditLog
    from app.models.history import ListeningHistory
    from app.models.starred import StarredAlbum, StarredArtist, StarredTrack

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

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Subsonic authentication
    subsonic_password: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subsonic_salt: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    credentials: Mapped[list["ServiceCredentials"]] = relationship("ServiceCredentials", back_populates="user", cascade=CASCADE_DELETE)
    downloads: Mapped[list["Download"]] = relationship("Download", back_populates="user", cascade=CASCADE_DELETE)
    playlists: Mapped[list["Playlist"]] = relationship("Playlist", back_populates="owner", cascade=CASCADE_DELETE)
    watchlist: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user", cascade=CASCADE_DELETE)
    starred_artists: Mapped[list["StarredArtist"]] = relationship("StarredArtist", back_populates="user", cascade=CASCADE_DELETE)
    starred_albums: Mapped[list["StarredAlbum"]] = relationship("StarredAlbum", back_populates="user", cascade=CASCADE_DELETE)
    starred_tracks: Mapped[list["StarredTrack"]] = relationship("StarredTrack", back_populates="user", cascade=CASCADE_DELETE)
    history: Mapped[list["ListeningHistory"]] = relationship("ListeningHistory", back_populates="user", cascade=CASCADE_DELETE)
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade=CASCADE_DELETE)

    # Preferences (JSONB)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=default_preferences)
