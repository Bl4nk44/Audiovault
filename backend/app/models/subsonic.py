"""
Subsonic-specific ORM models.

These models support Subsonic API functionality that doesn't map
directly to existing Audiovault models.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


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
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Token is a random string, salt is used by client for MD5 hashing
    token = Column(String(64), unique=True, nullable=False)
    salt = Column(String(32), nullable=False)
    
    # Client identification
    client_name = Column(String(100), nullable=True)
    client_version = Column(String(50), nullable=True)
    
    # Lifecycle
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", backref="subsonic_tokens")
    
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
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Rating value 0-5 (0 = unrated)
    rating = Column(Integer, nullable=False, default=0)
    
    rated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    
    # Relationships
    user = relationship("User", backref="subsonic_ratings")
    track = relationship("Track", backref="subsonic_ratings")
    
    __table_args__ = (
        Index("ix_subsonic_ratings_user_track", "user_id", "track_id", unique=True),
    )


class SubsonicNowPlaying(Base):
    """
    Currently playing tracks (for getNowPlaying endpoint).
    
    This is a lightweight table that gets updated frequently.
    Entries older than 5 minutes can be considered stale.
    """
    
    __tablename__ = "subsonic_now_playing"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Playback info
    client_name = Column(String(100), nullable=True)
    player_id = Column(String(100), nullable=True)  # Unique player instance
    
    # Timestamps
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    
    # Position in seconds
    position_seconds = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", backref="subsonic_now_playing")
    track = relationship("Track", backref="subsonic_now_playing")
    
    __table_args__ = (
        Index("ix_subsonic_now_playing_user", "user_id"),
        Index("ix_subsonic_now_playing_updated", "updated_at"),
    )
