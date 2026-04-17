from typing import Annotated
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.services.watchlist_engine import watchlist_engine
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class WatchlistAddRequest(BaseModel):
    watch_type: str
    source: str
    source_id: str
    source_name: str
    image_url: str | None = None
    metadata_content: dict | None = {}
    auto_download: bool = False


@router.post("/add")
async def add_to_watchlist(
    request: WatchlistAddRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Watchlist add request: {request.dict()}"
    )  # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi.tainted-log-injection-stdlib-fastapi
    return await watchlist_engine.add_to_watchlist(db, current_user.id, request.dict())


@router.get("/list")
async def get_watchlist(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    return await watchlist_engine.get_watchlist(db, current_user.id)


@router.delete("/remove/{watchlist_id}")
async def remove_from_watchlist(
    watchlist_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    success = await watchlist_engine.remove_from_watchlist(db, watchlist_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success"}


class WatchlistUpdateRequest(BaseModel):
    auto_download: bool


@router.patch("/{watchlist_id}")
async def update_watchlist_item(
    watchlist_id: UUID,
    request: WatchlistUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    item = await watchlist_engine.update_watchlist_item(
        db, watchlist_id, current_user.id, request.dict(exclude_unset=True)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/check-updates")
async def check_updates(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    count = await watchlist_engine.check_for_updates(db, current_user.id)
    return {"status": "success", "new_downloads": count}
