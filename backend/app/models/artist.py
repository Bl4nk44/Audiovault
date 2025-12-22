from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.base import Base

class Artist(Base):
    __tablename__ = "artists"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(500), index=True, nullable=False)
    bio = Column(Text, nullable=True)
    
    # External IDs
    spotify_id = Column(String(100), nullable=True, unique=True)
    deezer_id = Column(String(100), nullable=True, unique=True)
    
    # Images (profile, banner, etc.)
    images = Column(JSON, default={})
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    albums = relationship("Album", back_populates="artist")
    tracks = relationship("Track", back_populates="artist_rel") # Renamed to avoid confusion with string column
