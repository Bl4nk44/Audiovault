"""
Utility functions for Subsonic API.

ID encoding/decoding, time formatting, and other helpers.
"""

from datetime import datetime
from typing import Any
from uuid import UUID


def format_subsonic_date(dt: datetime | None) -> str | None:
    """
    Format datetime for Subsonic API.
    
    Subsonic uses ISO 8601 format: 2024-01-15T10:30:00.000Z
    
    Args:
        dt: Datetime to format
        
    Returns:
        ISO 8601 formatted string or None
    """
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def format_duration(duration_ms: int | None) -> int:
    """
    Convert milliseconds to seconds for Subsonic.
    
    Subsonic uses seconds for duration.
    
    Args:
        duration_ms: Duration in milliseconds
        
    Returns:
        Duration in seconds
    """
    if duration_ms is None:
        return 0
    return duration_ms // 1000


def parse_subsonic_id(subsonic_id: str) -> UUID:
    """
    Parse Subsonic ID to UUID.
    
    Subsonic IDs in Audiovault are just UUID strings.
    
    Args:
        subsonic_id: ID from Subsonic client
        
    Returns:
        UUID object
        
    Raises:
        ValueError: If ID is not a valid UUID
    """
    return UUID(subsonic_id)


def to_subsonic_id(uuid_obj: UUID) -> str:
    """
    Convert UUID to Subsonic ID.
    
    Args:
        uuid_obj: UUID to convert
        
    Returns:
        String representation of UUID
    """
    return str(uuid_obj)


def get_cover_art_id(
    track_id: UUID | None = None,
    album_id: UUID | None = None,
    artist_id: UUID | None = None,
) -> str | None:
    """
    Generate cover art ID for Subsonic.
    
    We prefix IDs with type to distinguish them in getCoverArt.
    
    Args:
        track_id: Track UUID
        album_id: Album UUID  
        artist_id: Artist UUID
        
    Returns:
        Cover art ID string or None
    """
    if album_id:
        return f"al-{album_id}"
    if track_id:
        return f"tr-{track_id}"
    if artist_id:
        return f"ar-{artist_id}"
    return None


def parse_cover_art_id(cover_art_id: str) -> tuple[str, UUID]:
    """
    Parse cover art ID to type and UUID.
    
    Args:
        cover_art_id: Cover art ID (e.g., "al-uuid" or just "uuid")
        
    Returns:
        Tuple of (type, UUID) where type is 'al', 'tr', 'ar', or 'unknown'
    """
    if "-" in cover_art_id and len(cover_art_id.split("-")[0]) <= 2:
        parts = cover_art_id.split("-", 1)
        item_type = parts[0]
        uuid_str = parts[1]
    else:
        item_type = "unknown"
        uuid_str = cover_art_id
    
    return item_type, UUID(uuid_str)


def get_content_type(file_path: str) -> str:
    """
    Get MIME type from file extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        MIME type string
    """
    ext = file_path.lower().split(".")[-1] if "." in file_path else ""
    
    mime_types = {
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "wav": "audio/wav",
        "wma": "audio/x-ms-wma",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    
    return mime_types.get(ext, "application/octet-stream")


def build_song_response(
    track: Any,
    download: Any | None = None,
    include_path: bool = False,
) -> dict:
    """
    Build Subsonic song/child response from Track.
    
    Args:
        track: Track model instance
        download: Optional Download model with file info
        include_path: Include file path in response
        
    Returns:
        Dict with Subsonic song fields
    """
    metadata = track.metadata_content or {}
    
    song = {
        "id": str(track.id),
        "title": track.title or "Unknown",
        "artist": track.artist or "Unknown Artist",
        "album": track.album or "Unknown Album",
        "duration": format_duration(track.duration_ms),
        "isDir": False,
        "isVideo": False,
        "type": "music",
        "created": format_subsonic_date(track.created_at),
    }
    
    # Optional fields
    if track.artist_id:
        song["artistId"] = str(track.artist_id)
    
    if track.album_id:
        song["albumId"] = str(track.album_id)
        song["coverArt"] = f"al-{track.album_id}"
    elif metadata.get("image_url"):
        song["coverArt"] = str(track.id)
    
    if metadata.get("genre"):
        song["genre"] = metadata["genre"]
    
    if metadata.get("year"):
        song["year"] = metadata["year"]
    
    if track.isrc:
        song["musicBrainzId"] = track.isrc  # Not exact but useful
    
    # File info from download
    if download:
        song["suffix"] = download.file_path.split(".")[-1] if download.file_path else "mp3"
        song["size"] = download.file_size or 0
        song["bitRate"] = 320  # Default, could be detected
        song["contentType"] = get_content_type(download.file_path) if download.file_path else "audio/mpeg"
        
        if include_path:
            song["path"] = download.file_path
    
    return song


def build_album_response(album: Any, song_count: int = 0) -> dict:
    """
    Build Subsonic album response from Album model.
    
    Args:
        album: Album model instance
        song_count: Number of songs in album
        
    Returns:
        Dict with Subsonic album fields
    """
    
    return {
        "id": str(album.id),
        "name": album.title or "Unknown Album",
        "artist": album.artist.name if album.artist else "Unknown Artist",
        "artistId": str(album.artist_id) if album.artist_id else None,
        "coverArt": f"al-{album.id}",
        "songCount": song_count,
        "duration": 0,  # Would need to sum tracks
        "created": format_subsonic_date(album.created_at),
        "year": int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None,
        "isDir": True,
    }


def build_artist_response(artist: Any, album_count: int = 0) -> dict:
    """
    Build Subsonic artist response from Artist model.
    
    Args:
        artist: Artist model instance
        album_count: Number of albums
        
    Returns:
        Dict with Subsonic artist fields
    """
    images = artist.images or {}
    
    return {
        "id": str(artist.id),
        "name": artist.name or "Unknown Artist",
        "albumCount": album_count,
        "coverArt": f"ar-{artist.id}" if images else None,
    }
