from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.playlist_version import PlaylistVersion
    from app.models.track import Track
    from app.models.user import User


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    __table_args__ = (Index("ix_playlist_tracks_order", "playlist_id", "order"),)

    playlist_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("playlists.id"), primary_key=True)
    track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tracks.id"), primary_key=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    playlist: Mapped[Playlist] = relationship("Playlist", back_populates="tracks")
    track: Mapped[Track] = relationship("Track")


class Playlist(Base):
    __tablename__ = "playlists"

    __table_args__ = (Index("ix_playlists_owner_name", "owner_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    owner: Mapped[User] = relationship("User", back_populates="playlists")
    tracks: Mapped[list[PlaylistTrack]] = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.order",
    )
    versions: Mapped[list[PlaylistVersion]] = relationship(
        "PlaylistVersion",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistVersion.version_number.desc()",
    )
