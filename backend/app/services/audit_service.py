"""
Audit service for logging user actions.
"""

import logging
from uuid import UUID

from app.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for creating and managing audit logs.
    Provides methods to log various user actions.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
        user_id: UUID | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            db: Database session
            action: Type of action (CREATE, UPDATE, DELETE, LOGIN, etc.)
            resource_type: Type of resource affected (playlist, track, user)
            resource_id: ID of the affected resource
            user_id: ID of the user performing the action
            details: Additional details about the action
            ip_address: Client IP address
            user_agent: Client user agent string
            endpoint: API endpoint called
            method: HTTP method used

        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
        )

        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)

        logger.info(f"Audit: {action} {resource_type} (id={resource_id}) by user {user_id}")

        return audit_log

    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> AuditLog:
        """Log a login attempt."""
        return await AuditService.log(
            db=db,
            action="LOGIN_SUCCESS" if success else "LOGIN_FAILED",
            resource_type="auth",
            user_id=user_id if success else None,
            details={"user_id": str(user_id), "success": success},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_logout(
        db: AsyncSession,
        user_id: UUID,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a logout."""
        return await AuditService.log(
            db=db,
            action="LOGOUT",
            resource_type="auth",
            user_id=user_id,
            ip_address=ip_address,
        )

    @staticmethod
    async def log_create(
        db: AsyncSession,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a resource creation."""
        return await AuditService.log(
            db=db,
            action="CREATE",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    async def log_update(
        db: AsyncSession,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a resource update with before/after values."""
        return await AuditService.log(
            db=db,
            action="UPDATE",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details={"old": old_values, "new": new_values},
            ip_address=ip_address,
        )

    @staticmethod
    async def log_delete(
        db: AsyncSession,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a resource deletion."""
        return await AuditService.log(
            db=db,
            action="DELETE",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )


# Singleton instance
audit_service = AuditService()
