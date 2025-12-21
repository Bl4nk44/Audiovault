from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class Album(Base):
    __tablename__ = "albums"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), index=True, nullable=False)
    release_date = Column(String(50), nullable=True) # Full date or just year
    total_tracks = Column(Integer, nullable=True)
    
    artist_id = Column(Uuid(as_uuid=True), ForeignKey("artists.id"), nullable=True)
    
    # External IDs
    spotify_id = Column(String(100), nullable=True, unique=True)
    deezer_id = Column(String(100), nullable=True, unique=True)
    
    # Images (cover art)
    images = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album_rel")
