"""
Audit Log model for tracking user actions.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuditLog(Base):
    """
    Model for storing audit logs of user actions.

    Tracks CREATE, UPDATE, DELETE operations on resources
    with detailed information about what changed.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Action type: CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    action = Column(String(50), nullable=False, index=True)

    # Resource being affected
    resource_type = Column(String(100), nullable=False)  # e.g., "playlist", "track", "user"
    resource_id = Column(Uuid(as_uuid=True), nullable=True)

    # Details of the action (what changed, old/new values, etc.)
    details = Column(JSON, default={})

    # HTTP request info
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type} by user {self.user_id}>"
