from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)

    # What to watch
    watch_type = Column(String(20))  # artist, playlist, channel
    source = Column(String(20))  # spotify, youtube, deezer
    source_id = Column(String(100))  # platform-specific ID
    source_name = Column(String(255))  # "The Weeknd", "Pop Hits"

    # Settings
    auto_download = Column(Boolean, default=False)
    check_interval_hours = Column(Integer, default=24)

    # Status
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    new_items_count = Column(Integer, default=0)

    # Metadata
    metadata_content = Column("metadata", JSON, default={})

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="watchlist")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "source_id", "source", name="unique_watch"),)
