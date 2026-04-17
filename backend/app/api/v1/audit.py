"""
Audit logs API endpoint.
Admin-only access to view audit logs.
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Error message constant
ADMIN_ACCESS_REQUIRED = "Admin access required"


class AuditLogResponse(BaseModel):
    """Response model for a single audit log entry."""

    id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    details: dict
    ip_address: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response model for paginated audit logs."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    action: Annotated[Optional[str], Query(description="Filter by action type")] = None,
    resource_type: Annotated[Optional[str], Query(description="Filter by resource type")] = None,
    user_id: Annotated[Optional[UUID], Query(description="Filter by user ID")] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    List audit logs with pagination and filtering.
    Only accessible by admin users.
    """
    # Check if user is admin (by username for simplicity)
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail=ADMIN_ACCESS_REQUIRED)

    # Build query
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    # Order by created_at descending
    query = query.order_by(desc(AuditLog.created_at))

    # Count total
    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(logs) < total,
    )


@router.get("/actions", response_model=list[str])
async def list_action_types(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get list of all action types in audit logs.
    """
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail=ADMIN_ACCESS_REQUIRED)

    result = await db.execute(select(AuditLog.action).distinct())
    actions = [row[0] for row in result.fetchall()]
    return actions


@router.get("/resources", response_model=list[str])
async def list_resource_types(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get list of all resource types in audit logs.
    """
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail=ADMIN_ACCESS_REQUIRED)

    result = await db.execute(select(AuditLog.resource_type).distinct())
    resources = [row[0] for row in result.fetchall()]
    return resources
