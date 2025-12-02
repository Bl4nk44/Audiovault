from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.history import ListeningHistory
from app.models.recommendation import PlaylistRecommendation
from app.models.track import Track
from app.models.user import User
from datetime import datetime, timedelta
import random
import json
from uuid import uuid4

class AIService:
    async def generate_weekly_playlist(self, db: AsyncSession, user_id: str):
        # Check if weekly playlist already exists for this week
        start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await db.execute(
            select(PlaylistRecommendation)
            .where(PlaylistRecommendation.user_id == user_id)
            .where(PlaylistRecommendation.type == 'weekly')
            .where(PlaylistRecommendation.created_at >= start_of_week)
        )
        existing = result.scalars().first()
        
        if existing:
            return existing

        # Analyze history (Mock AI)
        # Get top artists from last 30 days
        last_30_days = datetime.utcnow() - timedelta(days=30)
        history_result = await db.execute(
            select(ListeningHistory)
            .where(ListeningHistory.user_id == user_id)
            .where(ListeningHistory.played_at >= last_30_days)
        )
        history = history_result.scalars().all()
        
        # Simple heuristic: Get random tracks from DB for now
        # In a real scenario, we would use the history to query Spotify/YouTube for recommendations
        tracks_result = await db.execute(select(Track).limit(50))
        all_tracks = tracks_result.scalars().all()
        
        if not all_tracks:
            return None

        selected_tracks = random.sample(all_tracks, min(len(all_tracks), 10))
        
        track_list = []
        for track in selected_tracks:
            track_list.append({
                "id": str(track.id),
                "title": track.title,
                "artist": track.artist,
                "image_url": track.image_url,
                "source": track.source,
                "duration_ms": track.duration_ms
            })

        recommendation = PlaylistRecommendation(
            user_id=user_id,
            title=f"Weekly Vibe {datetime.utcnow().strftime('%V')}",
            description="AI-curated playlist based on your recent listening habits.",
            type="weekly",
            tracks=track_list
        )
        
        db.add(recommendation)
        await db.commit()
        await db.refresh(recommendation)
        
        return recommendation

    async def update_profile(self, db: AsyncSession, user_id: str):
        from app.models.profile import ListenerProfile
        
        # Get recent history
        last_90_days = datetime.utcnow() - timedelta(days=90)
        history_result = await db.execute(
            select(ListeningHistory)
            .where(ListeningHistory.user_id == user_id)
            .where(ListeningHistory.played_at >= last_90_days)
            .options(joinedload(ListeningHistory.track))
        )
        history = history_result.scalars().all()
        
        if not history:
            return None
            
        # Calculate top artists/genres (Mock logic)
        artist_counts = {}
        for entry in history:
            if entry.track and entry.track.artist:
                artist_counts[entry.track.artist] = artist_counts.get(entry.track.artist, 0) + 1
                
        top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_artists_list = [{"name": name, "count": count} for name, count in top_artists]
        
        # Mock Vibe Description
        vibe = "Eclectic Explorer"
        if top_artists:
            vibe = f"Fan of {top_artists[0][0]} and similar sounds"

        # Update or Create Profile
        result = await db.execute(select(ListenerProfile).where(ListenerProfile.user_id == user_id))
        profile = result.scalars().first()
        
        if not profile:
            profile = ListenerProfile(user_id=user_id)
            db.add(profile)
            
        profile.top_artists = top_artists_list
        profile.vibe_description = vibe
        profile.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(profile)
        return profile

    async def generate_discovery_playlist(self, db: AsyncSession, user_id: str):
        # Check if discovery playlist already exists for this week
        start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await db.execute(
            select(PlaylistRecommendation)
            .where(PlaylistRecommendation.user_id == user_id)
            .where(PlaylistRecommendation.type == 'discovery')
            .where(PlaylistRecommendation.created_at >= start_of_week)
        )
        existing = result.scalars().first()
        
        if existing:
            return existing

        # Get tracks NOT in history (Mock Discovery)
        # In real app: Query Spotify for "New Releases" based on profile genres
        
        subquery = select(ListeningHistory.track_id).where(ListeningHistory.user_id == user_id)
        tracks_result = await db.execute(
            select(Track).where(Track.id.not_in(subquery)).limit(50)
        )
        all_tracks = tracks_result.scalars().all()
        
        if not all_tracks:
            # Fallback if user has listened to everything (unlikely) or DB empty
            tracks_result = await db.execute(select(Track).limit(20))
            all_tracks = tracks_result.scalars().all()

        selected_tracks = random.sample(all_tracks, min(len(all_tracks), 15))
        
        track_list = []
        for track in selected_tracks:
            track_list.append({
                "id": str(track.id),
                "title": track.title,
                "artist": track.artist,
                "image_url": track.image_url,
                "source": track.source,
                "duration_ms": track.duration_ms
            })

        recommendation = PlaylistRecommendation(
            user_id=user_id,
            title=f"Discover Weekly",
            description="Fresh finds selected just for you.",
            type="discovery",
            tracks=track_list
        )
        
        db.add(recommendation)
        await db.commit()
        await db.refresh(recommendation)
        
        return recommendation

ai_service = AIService()
