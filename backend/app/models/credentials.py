from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.db.base import Base

class ServiceCredentials(Base):
    __tablename__ = "service_credentials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    service = Column(String(50)) # spotify, youtube, deezer
    access_token = Column(String(2000), nullable=True)
    refresh_token = Column(String(2000), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Additional info (e.g. scopes, token_type)
    extra_data = Column(JSON, default={})
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="credentials")
