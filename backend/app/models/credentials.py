from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class ServiceCredentials(Base):
    __tablename__ = "service_credentials"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)

    service = Column(String(50))  # spotify, youtube, deezer
    access_token = Column(String(2000), nullable=True)
    refresh_token = Column(String(2000), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Additional info (e.g. scopes, token_type)
    extra_data = Column(JSON, default={})

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="credentials")
