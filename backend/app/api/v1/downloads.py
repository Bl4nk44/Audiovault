from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List
from app.db.database import get_db
from app.services.download_manager import download_manager
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.download import Download
from pydantic import BaseModel
from uuid import UUID

router = APIRouter()

class DownloadRequest(BaseModel):
    track_id: UUID
    source: str

@router.post("/add")
async def add_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await download_manager.add_download(db, current_user.id, request.track_id, request.source)

@router.get("/queue")
async def get_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Download)
        .options(joinedload(Download.track))
        .where(Download.user_id == current_user.id)
        .order_by(Download.created_at.desc())
    )
    return result.scalars().all()
