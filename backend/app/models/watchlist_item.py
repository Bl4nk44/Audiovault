from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.watchlist import Watchlist
    from app.models.track import Track


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    watchlist_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("watchlist.id"), index=True, nullable=False)
    track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tracks.id"), index=True, nullable=False)

    # Metadata for the item in the context of this playlist
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Track order
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    watchlist: Mapped["Watchlist"] = relationship("Watchlist", back_populates="items")
    track: Mapped["Track"] = relationship("Track", back_populates="watchlist_items")

    __table_args__ = (UniqueConstraint("watchlist_id", "track_id", name="unique_watchlist_track"),)
