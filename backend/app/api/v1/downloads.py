import logging
import os
from typing import Annotated
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.download import Download
from app.models.user import User
from app.schemas.download import DownloadCreate
from app.services.download_manager import download_manager
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

SPOTIFY_CONFIG_ERROR = "Spotify service not configured"
_logger = logging.getLogger(__name__)


async def _ensure_track_in_db(db: AsyncSession, track_data: dict, source: str):
    from app.models.track import Track

    id_field_map = {"deezer": "deezer_id", "spotify": "spotify_id", "youtube": "youtube_id"}
    id_field = id_field_map.get(source)
    raw_id = str(track_data.get("id", ""))
    if id_field:
        result = await db.execute(select(Track).where(getattr(Track, id_field) == raw_id))
        track_obj = result.scalar_one_or_none()
        if track_obj:
            return track_obj

    meta: dict = {"image_url": track_data.get("image_url"), "album": track_data.get("album")}
    kwargs: dict = {
        "title": track_data["title"],
        "artist": track_data["artist"],
        "duration_ms": track_data.get("duration_ms"),
        "metadata_source": source,
        "metadata_content": meta,
    }
    if source == "spotify":
        meta["album_art"] = track_data.get("image_url")
        meta["isrc"] = track_data.get("isrc")
        kwargs["spotify_id"] = raw_id
    elif source == "deezer":
        kwargs["deezer_id"] = raw_id
        kwargs["isrc"] = track_data.get("isrc")
    elif source == "youtube":
        kwargs["youtube_id"] = raw_id
    track_obj = Track(**kwargs)
    db.add(track_obj)
    await db.flush()
    return track_obj


async def _queue_tracks(db: AsyncSession, user_id, tracks: list, source: str, playlist_name: str) -> int:
    count = 0
    for track_data in tracks:
        track_obj = await _ensure_track_in_db(db, track_data, source)
        try:
            await download_manager.add_download(
                db, user_id, DownloadCreate(track_id=track_obj.id, source=source, playlist_name=playlist_name)
            )
            count += 1
        except Exception as e:
            # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi.tainted-log-injection-stdlib-fastapi
            _logger.warning(f"Failed to queue track {track_data.get('title')}: {e}")
    return count


async def _resolve_spotify_id(db: AsyncSession, track_id_str: str) -> UUID:
    from app.models.track import Track

    result = await db.execute(select(Track).where(Track.spotify_id == track_id_str))
    track_obj = result.scalar_one_or_none()
    if not track_obj:
        from app.services.spotify_service import SpotifyService

        track_data = await SpotifyService().get_track(track_id_str)
        if not track_data:
            raise HTTPException(status_code=404, detail="Track not found on Spotify")
        track_obj = await _ensure_track_in_db(db, {**track_data, "id": track_id_str}, "spotify")
    return track_obj.id


async def _resolve_deezer_id(db: AsyncSession, track_id_str: str) -> UUID:
    from app.models.track import Track

    result = await db.execute(select(Track).where(Track.deezer_id == track_id_str))
    track_obj = result.scalar_one_or_none()
    if not track_obj:
        from app.services.deezer_service import DeezerService

        track_data = await DeezerService().get_track(track_id_str)
        if not track_data:
            raise HTTPException(status_code=404, detail="Track not found on Deezer")
        track_obj = await _ensure_track_in_db(db, {**track_data, "id": track_id_str}, "deezer")
    return track_obj.id


async def _resolve_musicbrainz_id(db: AsyncSession, track_id_str: str) -> UUID:
    from app.models.track import Track

    result = await db.execute(select(Track).where(Track.musicbrainz_id == track_id_str))
    track_obj = result.scalar_one_or_none()
    if not track_obj:
        from app.services.musicbrainz_service import MusicBrainzService

        track_data = await MusicBrainzService().get_track_by_isrc(track_id_str)
        if not track_data:
            raise HTTPException(status_code=404, detail="Track not found on MusicBrainz")
        track_obj = Track(
            title=track_data["title"],
            artist=track_data["artist"],
            musicbrainz_id=track_data.get("id"),
            isrc=track_data.get("isrc"),
            duration_ms=track_data.get("duration_ms"),
            metadata_source="musicbrainz",
            metadata_content={"album": track_data.get("album")},
        )
        db.add(track_obj)
        await db.flush()
    return track_obj.id


async def _resolve_youtube_id(db: AsyncSession, track_id_str: str) -> UUID:
    from app.models.track import Track

    result = await db.execute(select(Track).where(Track.youtube_id == track_id_str))
    track_obj = result.scalar_one_or_none()
    if track_obj:
        return track_obj.id
    raise HTTPException(
        status_code=400,
        detail="YouTube track resolution from ID not yet implemented. Please add to library from search results first.",
    )


async def _resolve_track_to_local_id(db: AsyncSession, track_id_str: str, source: str) -> UUID:
    """Resolve a possibly external track ID to a local UUID."""
    from app.models.track import Track

    try:
        potential_uuid = UUID(track_id_str)
        result = await db.execute(select(Track).where(Track.id == potential_uuid))
        track_obj = result.scalar_one_or_none()
        if track_obj:
            return track_obj.id
    except ValueError, AttributeError:
        pass

    resolvers = {
        "spotify": _resolve_spotify_id,
        "deezer": _resolve_deezer_id,
        "musicbrainz": _resolve_musicbrainz_id,
        "youtube": _resolve_youtube_id,
    }
    resolver = resolvers.get(source)
    if not resolver:
        raise HTTPException(
            status_code=400,
            detail=f"Track ID {track_id_str} not found and source {source} does not support resolution",
        )
    return await resolver(db, track_id_str)


class DownloadRequest(BaseModel):
    track_id: str  # Changed from UUID to str to support external IDs
    source: str
    playlist_name: str | None = None


class TrackResponse(BaseModel):
    id: UUID
    title: str
    artist: str
    image_url: str | None = None


@router.post("/add", responses={404: {"description": "Not found"}, 400: {"description": "Bad request"}})
async def add_download(
    request: DownloadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    local_track_id = await _resolve_track_to_local_id(db, request.track_id, request.source)

    download_data = DownloadCreate(
        track_id=local_track_id,
        source=request.source,
        playlist_name=request.playlist_name,
    )
    res = await download_manager.add_download(db, current_user.id, download_data)
    await db.commit()
    return res


@router.post("/{download_id}/pause")
async def pause_download(download_id: UUID, current_user: Annotated[User, Depends(get_current_active_user)] = ...):
    await download_manager.pause_download(str(download_id))
    return {"status": "success"}


@router.post("/{download_id}/resume")
async def resume_download(
    download_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    await download_manager.resume_download(db, str(download_id))
    return {"status": "success"}


@router.post("/{download_id}/retry")
async def retry_download(
    download_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    await download_manager.resume_download(db, str(download_id))
    return {"status": "success"}


@router.delete("/{download_id}", responses={404: {"description": "Not found"}})  # Standardized path
async def remove_download(
    download_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    # First check if file exists to delete it (as cancel_download deletes the DB record)
    result = await db.execute(select(Download).where(Download.id == download_id, Download.user_id == current_user.id))
    download = result.scalar_one_or_none()

    if not download:
        raise HTTPException(status_code=404, detail="Download not found")

    file_path = download.file_path

    # Use manager to cancel task and delete from DB
    await download_manager.cancel_download(db, str(download_id))

    # Delete physical file
    if file_path and os.path.exists(file_path):
        try:
            from pathlib import Path

            from app.core.config import settings

            base_dir = Path(settings.DOWNLOAD_DIR).resolve()
            target_path = Path(file_path).resolve()

            if target_path.is_relative_to(base_dir):
                os.remove(
                    file_path
                )  # nosemgrep: python.fastapi.file.tainted-path-traversal-stdlib-fastapi.tainted-path-traversal-stdlib-fastapi  # noqa: E501
        except OSError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error deleting file {file_path}: {e}"
            )  # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi.tainted-log-injection-stdlib-fastapi  # noqa: E501

    return {"status": "success"}


@router.delete("/library/playlist")
async def delete_playlist(
    source: str,
    playlist_name: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Delete an entire playlist and its contents."""
    await download_manager.delete_playlist(db, str(current_user.id), source, playlist_name)
    return {"status": "success", "message": f"Playlist {playlist_name} deleted"}


class ArtistDownloadRequest(BaseModel):
    source: str = "deezer"


@router.post(
    "/artist/{artist_id}/download-all",
    responses={404: {"description": "Not found"}, 400: {"description": "Bad request"}},
)
async def download_all_artist_tracks(
    artist_id: str,
    request: ArtistDownloadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Download all tracks from an artist's discography.
    Creates a folder with the artist's name and downloads all albums/singles.
    """
    all_tracks: list = []
    artist_name: str

    if request.source == "deezer":
        from app.services.deezer_service import DeezerService

        service = DeezerService()
        artist = await service.get_artist_details(artist_id)
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        artist_name = artist["name"]
        all_tracks = list(artist.get("top_tracks", []))
        for album in artist.get("albums", []):
            all_tracks.extend(await service.get_album_tracks(album["id"]))
    elif request.source == "spotify":
        from app.services.spotify_service import SpotifyService

        service_sp = SpotifyService()
        artist = await service_sp.get_artist_details(artist_id)
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        artist_name = artist["name"]
        for album in await service_sp.get_artist_albums(artist_id):
            all_tracks.extend(await service_sp.get_album_tracks(album["id"]))
    else:
        raise HTTPException(status_code=400, detail=f"Source '{request.source}' not supported for artist downloads")

    queued_count = await _queue_tracks(db, current_user.id, all_tracks, request.source, artist_name)
    await db.commit()
    return {
        "status": "success",
        "artist": artist_name,
        "queued_count": queued_count,
        "message": f"Queued {queued_count} tracks from {artist_name}",
    }


@router.post(
    "/album/{album_id}/download",
    responses={404: {"description": "Not found"}, 400: {"description": "Bad request"}},
)
async def download_album(
    album_id: str,
    request: ArtistDownloadRequest,  # reusing this model as it just has 'source'
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Download all tracks from a specific album.
    Creates a folder with the Album name (or Artist/Album structure handled by manager).
    """
    album_name = "Unknown Album"
    tracks: list = []

    if request.source == "deezer":
        from app.services.deezer_service import DeezerService

        tracks = await DeezerService().get_album_tracks(album_id)
        if not tracks:
            raise HTTPException(status_code=404, detail="Album not found on Deezer")
        album_name = tracks[0].get("album", "Unknown Album") if tracks else album_id
    elif request.source == "spotify":
        from app.services.spotify_service import SpotifyService

        service = SpotifyService()
        try:
            album_data = await service.get_album_details(album_id)
            if not album_data:
                raise HTTPException(status_code=404, detail="Album not found")
            album_name = album_data["name"]
        except HTTPException:
            raise
        except Exception as e:
            # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi.tainted-log-injection-stdlib-fastapi
            _logger.error(f"Error fetching album {album_id}: {e}")
            raise HTTPException(status_code=404, detail="Album not found")
        tracks = await service.get_album_tracks(album_id)
    else:
        raise HTTPException(status_code=400, detail=f"Source '{request.source}' not supported for album downloads")

    queued_count = await _queue_tracks(db, current_user.id, tracks, request.source, album_name)
    await db.commit()
    return {
        "status": "success",
        "album": album_name,
        "queued_count": queued_count,
        "message": f"Queued {queued_count} tracks from {album_name}",
    }


@router.post("/rescan")
async def rescan_library(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    from app.services.library_maintenance import library_maintenance_service

    requeued_count = await library_maintenance_service.rescan_library_integrity(db, str(current_user.id))
    return {"status": "success", "rescanned_count": requeued_count}


@router.post("/clear-history")
async def clear_history(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    from app.services.library_maintenance import library_maintenance_service

    await library_maintenance_service.clear_history(db, str(current_user.id))
    return {"status": "success"}


@router.post("/restart-all")
async def restart_all(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Restart all failed/cancelled downloads."""
    count = await download_manager.restart_all_downloads(db, str(current_user.id))
    return {"status": "success", "count": count}


@router.get("/library/folders")
async def get_library_folders(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Returns the folder structure for the library: Service -> Playlists
    """
    # Get distinct sources
    result = await db.execute(
        select(Download.source, Download.playlist_name)
        .where(Download.user_id == current_user.id, Download.status == "completed")
        .distinct()
    )

    rows = result.all()

    # Construct grouping
    structure: dict[str, set[str]] = {}

    for row in rows:
        source = row[0] or "other"
        playlist = row[1]

        if source not in structure:
            structure[source] = set()

        if playlist:
            structure[source].add(playlist)

    # Convert sets to sorted lists
    response = {}
    for source, playlists in structure.items():
        response[source] = sorted(playlists)

    return response


@router.get("/library")
async def get_library(
    skip: int = 0,
    limit: int = 50,
    source: str | None = None,
    playlist: str | None = None,
    search: str | None = None,
    artist: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    from app.services.library_data import library_data_service

    return await library_data_service.get_library_items(
        db,
        str(current_user.id),
        skip,
        limit,
        source,
        playlist,
        search,
        artist,
        min_duration,
        max_duration,
    )


class BulkUpdateRequest(BaseModel):
    """Request model for bulk updating library items."""

    download_ids: list[UUID]
    updates: dict  # Fields to update: artist, title, album, genre, year


@router.put("/library/bulk-update", responses={400: {"description": "Bad request"}})
async def bulk_update_library_items(
    request: BulkUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Bulk update metadata for multiple library items at once.
    All specified items will receive the same updates.
    """
    from app.services.library_maintenance import library_maintenance_service

    if not request.download_ids:
        raise HTTPException(status_code=400, detail="No items specified")

    if len(request.download_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per request")

    # Validate allowed update fields
    allowed_fields = {"artist", "title", "album", "genre", "year", "playlist_name"}
    invalid_fields = set(request.updates.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}. Allowed: {', '.join(allowed_fields)}",
        )

    success_count = 0
    failed_ids = []

    for d_id in request.download_ids:
        try:
            await library_maintenance_service.update_download_item(db, str(current_user.id), str(d_id), request.updates)
            success_count += 1
        except Exception:
            failed_ids.append(str(d_id))

    return {
        "status": "success" if not failed_ids else "partial",
        "updated_count": success_count,
        "failed_count": len(failed_ids),
        "failed_ids": failed_ids[:10],
    }


@router.put(
    "/library/{download_id}",
    responses={404: {"description": "Not found"}, 400: {"description": "Bad request"}},
)
async def update_library_item(
    download_id: UUID,
    updates: dict,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    from app.services.library_maintenance import library_maintenance_service

    try:
        await library_maintenance_service.update_download_item(db, str(current_user.id), str(download_id), updates)
        return {"status": "success"}
    except ValueError as e:
        if str(e) == "Item not found":
            raise HTTPException(status_code=404, detail="Item not found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/queue")
async def get_queue(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    from app.services.library_data import library_data_service

    return await library_data_service.get_queue_items(db, str(current_user.id))


@router.post("/maintenance/fix-legacy-data")
async def fix_legacy_data(
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Diagnose and fix legacy data.
    """
    from app.services.library_maintenance import library_maintenance_service

    fixed_count = await library_maintenance_service.fix_legacy_data(db)
    return {"status": "success", "fixed_count": fixed_count}


@router.post("/maintenance/scan-library", responses={403: {"description": "Forbidden"}})
async def scan_library(
    scan_path: str | None = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Scans the DOWNLOAD_DIR (or custom scan_path) for mp3 files.
    """
    from app.services.library_scanner import library_scanner_service

    result = await library_scanner_service.scan_directory(db, str(current_user.id), scan_path)

    if result.get("status") == "error" and "Access denied" in result.get("message", ""):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=result["message"])

    return result
