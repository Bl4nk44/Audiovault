"""
Playlist versioning service for creating and managing version history.
"""

import logging
from uuid import UUID

from app.models.playlist import Playlist, PlaylistTrack
from app.models.playlist_version import PlaylistVersion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PlaylistVersionService:
    """
    Service for managing playlist version history.
    Creates snapshots when playlists are modified.
    """

    @staticmethod
    async def get_next_version_number(db: AsyncSession, playlist_id: UUID) -> int:
        """Get the next version number for a playlist."""
        result = await db.execute(
            select(func.max(PlaylistVersion.version_number)).where(PlaylistVersion.playlist_id == playlist_id)
        )
        current_max = result.scalar()
        return (current_max or 0) + 1

    @staticmethod
    async def create_snapshot(
        db: AsyncSession,
        playlist: Playlist,
        change_type: str,
        user_id: UUID | None = None,
        change_details: dict | None = None,
    ) -> PlaylistVersion:
        """
        Create a version snapshot of the playlist's current state.

        Args:
            db: Database session
            playlist: Playlist to snapshot
            change_type: Type of change (CREATE, ADD_TRACK, REMOVE_TRACK, etc.)
            user_id: User who made the change
            change_details: Additional details about the change

        Returns:
            Created PlaylistVersion instance
        """
        version_number = await PlaylistVersionService.get_next_version_number(db, playlist.id)

        # Get current track IDs in order
        result = await db.execute(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id).order_by(PlaylistTrack.order)
        )
        tracks = result.scalars().all()
        tracks_snapshot = [{"track_id": str(pt.track_id), "order": pt.order} for pt in tracks]

        version = PlaylistVersion(
            playlist_id=playlist.id,
            version_number=version_number,
            name=playlist.name,
            comment=playlist.comment,
            tracks_snapshot=tracks_snapshot,
            created_by=user_id,
            change_type=change_type,
            change_details=change_details or {},
        )

        db.add(version)
        await db.commit()
        await db.refresh(version)

        logger.info(f"Created version {version_number} for playlist {playlist.id} ({change_type})")

        return version

    @staticmethod
    async def get_versions(
        db: AsyncSession,
        playlist_id: UUID,
        limit: int = 50,
    ) -> list[PlaylistVersion]:
        """Get version history for a playlist."""
        result = await db.execute(
            select(PlaylistVersion)
            .where(PlaylistVersion.playlist_id == playlist_id)
            .order_by(PlaylistVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_version(
        db: AsyncSession,
        playlist_id: UUID,
        version_number: int,
    ) -> PlaylistVersion | None:
        """Get a specific version of a playlist."""
        result = await db.execute(
            select(PlaylistVersion).where(
                PlaylistVersion.playlist_id == playlist_id,
                PlaylistVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def rollback_to_version(
        db: AsyncSession,
        playlist: Playlist,
        version: PlaylistVersion,
        user_id: UUID,
    ) -> PlaylistVersion:
        """
        Rollback a playlist to a previous version.

        Args:
            db: Database session
            playlist: Playlist to rollback
            version: Version to rollback to
            user_id: User performing the rollback

        Returns:
            New PlaylistVersion created after rollback
        """
        # Restore metadata
        playlist.name = version.name
        playlist.comment = version.comment

        # Delete current tracks
        from sqlalchemy import delete

        await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id))

        # Restore tracks from snapshot
        for track_data in version.tracks_snapshot or []:
            track = PlaylistTrack(
                playlist_id=playlist.id,
                track_id=UUID(track_data["track_id"]),
                order=track_data["order"],
            )
            db.add(track)

        await db.commit()

        # Create new version recording the rollback
        new_version = await PlaylistVersionService.create_snapshot(
            db=db,
            playlist=playlist,
            change_type="ROLLBACK",
            user_id=user_id,
            change_details={
                "rolled_back_to_version": version.version_number,
            },
        )

        logger.info(f"Rolled back playlist {playlist.id} to version {version.version_number}")

        return new_version


# Singleton instance
playlist_version_service = PlaylistVersionService()
