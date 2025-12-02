from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    # What to watch
    watch_type = Column(String(20))  # artist, playlist, channel
    source = Column(String(20))      # spotify, youtube, deezer
    source_id = Column(String(100))  # platform-specific ID
    source_name = Column(String(255))  # "The Weeknd", "Pop Hits"
    
    # Settings
    auto_download = Column(Boolean, default=False)
    check_interval_hours = Column(Integer, default=24)
    
    # Status
    last_checked_at = Column(DateTime, nullable=True)
    new_items_count = Column(Integer, default=0)
    
    # Metadata
    metadata_content = Column("metadata", JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'source_id', 'source', name='unique_watch'),
    )
