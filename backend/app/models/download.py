from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class Download(Base):
    __tablename__ = "downloads"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    track_id = Column(Uuid(as_uuid=True), ForeignKey("tracks.id"))
    
    # Download details
    source = Column(String(20))  # spotify, youtube, deezer
    playlist_name = Column(String(255), nullable=True) # Name of the playlist if part of one
    status = Column(String(20), default="pending")  
    # pending, downloading, processing, completed, failed
    
    # Progress
    progress = Column(Integer, default=0)  # 0-100
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, default=0)  # bytes
    
    # Priority & Scheduling
    priority = Column(Integer, default=5)  # 1-10
    
    # Error tracking
    error_message = Column(String(1000), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # UI State
    archived = Column(Boolean, default=False) # If true, hidden from queue but visible in library
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="downloads")
    track = relationship("Track", back_populates="downloads")
