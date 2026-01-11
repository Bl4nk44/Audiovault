from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.base import Base


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    track_id = Column(Uuid(as_uuid=True), ForeignKey("tracks.id"))

    played_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    duration_played = Column(Integer)  # Seconds played

    # Relationships
    user = relationship("User", back_populates="history")
    track = relationship("Track")
