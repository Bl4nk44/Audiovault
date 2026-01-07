from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.models.artist import Artist
from app.schemas.artist import ArtistResponse

router = APIRouter()


@router.get("/", response_model=List[ArtistResponse])
async def get_artists(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Artist).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{artist_id}", response_model=ArtistResponse)
async def get_artist(artist_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Artist)
        .options(selectinload(Artist.albums), selectinload(Artist.tracks))
        .where(Artist.id == artist_id)
    )
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    return artist
