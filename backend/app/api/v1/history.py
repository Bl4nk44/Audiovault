from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.history import ListeningHistory
from app.models.track import Track
from pydantic import BaseModel
from uuid import UUID

router = APIRouter()


class HistoryRecord(BaseModel):
    track_id: UUID
    duration_played: int


@router.post("/record")
async def record_history(
    record: HistoryRecord,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify track exists
    track = await db.get(Track, record.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    history_entry = ListeningHistory(
        user_id=current_user.id,
        track_id=record.track_id,
        duration_played=record.duration_played,
    )
    db.add(history_entry)
    await db.commit()
    return {"status": "success"}
