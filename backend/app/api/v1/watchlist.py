from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.services.watchlist_engine import watchlist_engine
from app.core.dependencies import get_current_active_user
from app.models.user import User
from pydantic import BaseModel
from uuid import UUID

router = APIRouter()

class WatchlistAddRequest(BaseModel):
    watch_type: str
    source: str
    source_id: str
    source_name: str
    auto_download: bool = False

@router.post("/add")
async def add_to_watchlist(
    request: WatchlistAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await watchlist_engine.add_to_watchlist(db, current_user.id, request.dict())

@router.get("/list")
async def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await watchlist_engine.get_watchlist(db, current_user.id)

@router.delete("/remove/{watchlist_id}")
async def remove_from_watchlist(
    watchlist_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await watchlist_engine.remove_from_watchlist(db, watchlist_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success"}
