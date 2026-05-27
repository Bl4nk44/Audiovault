import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.download import Download
from app.models.track import Track
from app.models.watchlist_item import WatchlistItem


class WatchlistStorage:
    async def get_or_create_track(
        self, db: AsyncSession, track_data: dict, source: str, is_legacy_source: bool
    ) -> tuple[uuid.UUID, bool]:
        """Find or create a track and return its UUID and whether it was created."""
        existing_track = await self._find_existing_track(db, track_data, source)

        if existing_track:
            if not is_legacy_source:
                self._update_existing_track_metadata(db, existing_track, track_data, source)
            return existing_track.id, False
        else:
            new_track = self._create_new_track_instance(track_data, source, is_legacy_source)
            db.add(new_track)
            await db.commit()
            await db.refresh(new_track)
            return new_track.id, True

    async def _find_existing_track(self, db: AsyncSession, track_data: dict, source: str) -> Track | None:
        track_query = select(Track)
        if source == "spotify":
            track_query = track_query.where(Track.spotify_id == track_data["id"])
        elif source == "youtube":
            track_query = track_query.where(Track.youtube_id == track_data["id"])
        elif source == "deezer":
            track_query = track_query.where(Track.deezer_id == track_data["id"])
        else:
            track_query = track_query.where(Track.title == track_data["title"], Track.artist == track_data["artist"])
        result = await db.execute(track_query)
        return result.scalar_one_or_none()

    def _update_existing_track_metadata(self, db: AsyncSession, track: Track, track_data: dict, source: str):
        source_id_key = f"{source}_id"
        meta = dict(track.metadata_content or {})
        if source_id_key not in meta:
            meta[source_id_key] = track_data["id"]
            track.metadata_content = meta
            db.add(track)

    def _create_new_track_instance(self, track_data: dict, source: str, is_legacy_source: bool) -> Track:
        meta = {"image_url": track_data.get("image_url")}
        if not is_legacy_source:
            meta[f"{source}_id"] = track_data["id"]
            if track_data.get("source_url"):
                meta["source_url"] = track_data.get("source_url")

        track_kwargs = {
            "title": track_data["title"],
            "artist": track_data["artist"],
            "album": track_data.get("album"),
            "duration_ms": track_data.get("duration_ms"),
            "metadata_content": meta,
        }

        if source == "spotify":
            track_kwargs["spotify_id"] = track_data["id"]
        elif source == "youtube":
            track_kwargs["youtube_id"] = track_data["id"]
        elif source == "deezer":
            track_kwargs["deezer_id"] = track_data["id"]

        return Track(**track_kwargs)

    async def ensure_watchlist_item_link(
        self, db: AsyncSession, watchlist_id: str | uuid.UUID, track_id: str | uuid.UUID
    ):
        """Ensure the link between watchlist and track exists."""
        if isinstance(watchlist_id, uuid.UUID):
            w_uuid = watchlist_id
        else:
            w_uuid = uuid.UUID(str(watchlist_id))

        if isinstance(track_id, uuid.UUID):
            t_uuid = track_id
        else:
            t_uuid = uuid.UUID(str(track_id))

        wl_item_check = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == w_uuid,
                WatchlistItem.track_id == t_uuid,
            )
        )
        if not wl_item_check.scalar_one_or_none():
            new_wl_item = WatchlistItem(watchlist_id=watchlist_id, track_id=track_id, position=None)
            db.add(new_wl_item)
            await db.commit()

    async def get_existing_download_ids(self, db: AsyncSession, user_id: str | uuid.UUID, source: str) -> set[str]:
        """Get set of source IDs for tracks already downloaded by the user."""
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        downloaded_tracks_query = (
            select(Track)
            .join(Download, Download.track_id == Track.id)
            .where(Download.user_id == u_uuid, Download.archived.is_(False))
        )
        downloaded_tracks_result = await db.execute(downloaded_tracks_query)
        downloaded_tracks = downloaded_tracks_result.scalars().all()

        existing_ids = set()
        for t in downloaded_tracks:
            if source == "spotify" and t.spotify_id:
                existing_ids.add(t.spotify_id)
            elif source == "youtube" and t.youtube_id:
                existing_ids.add(t.youtube_id)
            elif source == "deezer" and t.deezer_id:
                existing_ids.add(t.deezer_id)
            else:
                source_id_key = f"{source}_id"
                if t.metadata_content and source_id_key in t.metadata_content:
                    existing_ids.add(t.metadata_content[source_id_key])
        return existing_ids
