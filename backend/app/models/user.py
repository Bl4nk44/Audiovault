from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    credentials = relationship("ServiceCredentials", back_populates="user", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="user", cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    history = relationship("ListeningHistory", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("PlaylistRecommendation", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("ListenerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Preferences (JSONB)
    preferences = Column(JSON, default={
        "theme": "dark",
        "quality": "high",
        "auto_download": False,
        "language": "en"
    })
