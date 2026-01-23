from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.watchlist_item import WatchlistItem


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)

    # What to watch
    watch_type: Mapped[str | None] = mapped_column(String(20))  # artist, playlist, channel
    source: Mapped[str | None] = mapped_column(String(20))  # spotify, youtube, deezer
    source_id: Mapped[str | None] = mapped_column(String(100))  # platform-specific ID
    source_name: Mapped[str | None] = mapped_column(String(255))  # "The Weeknd", "Pop Hits"

    # Settings
    auto_download: Mapped[bool] = mapped_column(Boolean, default=False)
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=24)

    # Status
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_items_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    metadata_content: Mapped[dict | None] = mapped_column("metadata", JSON, default={})

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watchlist")
    items: Mapped[list["WatchlistItem"]] = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "source_id", "source", name="unique_watch"),)
