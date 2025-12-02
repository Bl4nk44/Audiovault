from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List, Optional
from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.history import ListeningHistory
from app.models.recommendation import PlaylistRecommendation
from app.models.track import Track
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter()

class HistoryRecord(BaseModel):
    track_id: UUID
    duration_played: int

class RecommendationResponse(BaseModel):
    id: UUID
    title: str
    description: str
    type: str
    tracks: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/record")
async def record_history(
    record: HistoryRecord,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify track exists
    track = await db.get(Track, record.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    history_entry = ListeningHistory(
        user_id=current_user.id,
        track_id=record.track_id,
        duration_played=record.duration_played
    )
    db.add(history_entry)
    await db.commit()
    return {"status": "success"}

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PlaylistRecommendation)
        .where(PlaylistRecommendation.user_id == current_user.id)
        .order_by(PlaylistRecommendation.created_at.desc())
    )
    return result.scalars().all()

@router.post("/generate-weekly")
async def generate_weekly_recommendation(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.ai_service import ai_service
    recommendation = await ai_service.generate_weekly_playlist(db, current_user.id)
    return recommendation

@router.get("/profile")
async def get_listener_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.ai_service import ai_service
    # Update profile on fetch to ensure freshness
    profile = await ai_service.update_profile(db, current_user.id)
    return profile

@router.post("/generate-discovery")
async def generate_discovery_playlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.ai_service import ai_service
    recommendation = await ai_service.generate_discovery_playlist(db, current_user.id)
    return recommendation
