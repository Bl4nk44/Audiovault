"""
Playlist versioning model for tracking playlist history.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlaylistVersion(Base):
    """
    Model for storing playlist version snapshots.

    Each time a playlist is modified, a snapshot is created
    allowing users to view history and rollback to previous versions.
    """

    __tablename__ = "playlist_versions"

    __table_args__ = (
        Index("ix_playlist_versions_playlist_created", "playlist_id", "created_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    playlist_id = Column(
        Uuid(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    version_number = Column(Integer, nullable=False)

    # Snapshot of playlist metadata at this version
    name = Column(String, nullable=False)
    comment = Column(String, nullable=True)

    # Snapshot of tracks at this version (ordered list of track IDs)
    tracks_snapshot = Column(JSON, default=[])

    # Who made the change
    created_by = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # What kind of change
    change_type = Column(String(50), nullable=False)  # CREATE, ADD_TRACK, REMOVE_TRACK, REORDER, RENAME, etc.
    change_details = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    playlist = relationship("Playlist", back_populates="versions")
    creator = relationship("User")

    def __repr__(self) -> str:
        return f"<PlaylistVersion {self.playlist_id} v{self.version_number}>"
