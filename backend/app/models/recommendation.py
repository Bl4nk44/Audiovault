from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class PlaylistRecommendation(Base):
    __tablename__ = "playlist_recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    title = Column(String(255))
    description = Column(String(1000))
    tracks = Column(JSON)  # List of track objects or IDs
    type = Column(String(50))  # e.g., "weekly", "daily", "mood"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="recommendations")
