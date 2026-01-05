from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.base import Base

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    watchlist_id = Column(Uuid(as_uuid=True), ForeignKey("watchlist.id"), index=True, nullable=False)
    track_id = Column(Uuid(as_uuid=True), ForeignKey("tracks.id"), index=True, nullable=False)
    
    # Metadata for the item in the context of this playlist
    position = Column(Integer, nullable=True) # Track order
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")
    track = relationship("Track", back_populates="watchlist_items")
    
    __table_args__ = (
        UniqueConstraint('watchlist_id', 'track_id', name='unique_watchlist_track'),
    )
