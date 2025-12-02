from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class ListenerProfile(Base):
    __tablename__ = "listener_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    
    top_genres = Column(JSON, default={})
    top_artists = Column(JSON, default=[])
    vibe_description = Column(Text)
    
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="profile")
