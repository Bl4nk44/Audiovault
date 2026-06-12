"""
Subsonic-specific ORM models.

These models support Subsonic API functionality that doesn't map
directly to existing Audiovault models.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

_USERS_FK = "users.id"
_TRACKS_FK = "tracks.id"

if TYPE_CHECKING:
    from app.models.track import Track
    from app.models.user import User


class SubsonicAuthToken(Base):
    """
    Authentication tokens for Subsonic clients.

    Subsonic uses MD5(password+salt) for authentication, but since Audiovault
    uses bcrypt, we generate random tokens that clients can use instead.

    Flow:
    1. Client sends username + plaintext password to /getToken
    2. Server verifies with bcrypt and generates random token
    3. Client uses MD5(token+salt) for subsequent requests
    """

    __tablename__ = "subsonic_auth_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_USERS_FK, ondelete="CASCADE"),
        nullable=False,
    )

    # Token is a random string, salt is used by client for MD5 hashing
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    salt: Mapped[str] = mapped_column(String(32), nullable=False)

    # Client identification
    client_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Lifecycle
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    user: Mapped[User] = relationship("User", backref="subsonic_tokens")

    __table_args__ = (
        Index("ix_subsonic_auth_tokens_user_active", "user_id", "is_active"),
        Index("ix_subsonic_auth_tokens_token", "token"),
    )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(UTC) > self.expires_at


class SubsonicRating(Base):
    """
    User ratings for tracks (0-5 stars).

    Note: This is separate from StarredTrack which is boolean (starred/not starred).
    SubsonicRating stores the actual 0-5 rating value.
    """

    __tablename__ = "subsonic_ratings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_USERS_FK, ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_TRACKS_FK, ondelete="CASCADE"),
        nullable=False,
    )

    # Rating value 0-5 (0 = unrated)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[User] = relationship("User", backref="subsonic_ratings")
    track: Mapped[Track] = relationship("Track", backref="subsonic_ratings")

    __table_args__ = (Index("ix_subsonic_ratings_user_track", "user_id", "track_id", unique=True),)


class SubsonicNowPlaying(Base):
    """
    Currently playing tracks (for getNowPlaying endpoint).

    This is a lightweight table that gets updated frequently.
    Entries older than 5 minutes can be considered stale.
    """

    __tablename__ = "subsonic_now_playing"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_USERS_FK, ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_TRACKS_FK, ondelete="CASCADE"),
        nullable=False,
    )

    # Playback info
    client_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    player_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Unique player instance

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Position in seconds
    position_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped[User] = relationship("User", backref="subsonic_now_playing")
    track: Mapped[Track] = relationship("Track", backref="subsonic_now_playing")

    __table_args__ = (
        Index("ix_subsonic_now_playing_user", "user_id"),
        Index("ix_subsonic_now_playing_updated", "updated_at"),
    )


class SubsonicPlayQueue(Base):
    """
    Saved play queue per user (savePlayQueue / getPlayQueue).

    Subsonic stores a single play queue per user: an ordered list of track ids,
    the currently playing track, and the playback position. Re-saving replaces
    the previous queue, so there is at most one row per user.
    """

    __tablename__ = "subsonic_play_queues"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_USERS_FK, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Ordered list of track id strings in the queue
    track_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Currently playing track (may be absent from the queue if cleared)
    current_track_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_TRACKS_FK, ondelete="SET NULL"),
        nullable=True,
    )
    # Playback position within the current track, in milliseconds
    position_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Client that last saved the queue
    changed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship("User", backref="subsonic_play_queue")

    __table_args__ = (Index("ix_subsonic_play_queues_user", "user_id", unique=True),)


class SubsonicBookmark(Base):
    """
    Per-user playback bookmark for a track (createBookmark / getBookmarks).

    A bookmark marks a position within a track so playback can resume later.
    There is at most one bookmark per (user, track).
    """

    __tablename__ = "subsonic_bookmarks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_USERS_FK, ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(_TRACKS_FK, ondelete="CASCADE"),
        nullable=False,
    )

    # Position within the track, in milliseconds
    position_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship("User", backref="subsonic_bookmarks")
    track: Mapped[Track] = relationship("Track", backref="subsonic_bookmarks")

    __table_args__ = (Index("ix_subsonic_bookmarks_user_track", "user_id", "track_id", unique=True),)
