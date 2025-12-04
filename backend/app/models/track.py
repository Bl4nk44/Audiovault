from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class Track(Base):
    __tablename__ = "tracks"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), index=True, nullable=False)
    artist = Column(String(500), index=True, nullable=False)
    album = Column(String(500))
    duration_ms = Column(Integer)  # milliseconds
    
    # Service IDs (for cross-platform lookup)
    isrc = Column(String(20), unique=True, nullable=True)
    spotify_id = Column(String(100), nullable=True, unique=True)
    youtube_id = Column(String(100), nullable=True, unique=True)
    deezer_id = Column(String(100), nullable=True, unique=True)
    
    # Metadata
    metadata_content = Column("metadata", JSON, default={
        "image_url": None,
        "album_art": None,
        "genre": None,
        "year": None,
        "popularity": 0
    })
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    downloads = relationship("Download", back_populates="track")
