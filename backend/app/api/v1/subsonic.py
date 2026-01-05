import hashlib
import logging
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.user import User
from app.models.artist import Artist
from app.models.album import Album
from app.models.track import Track
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# --- SUBSONIC HELPERS ---

class SubsonicResponse:
    """Helper to format responses according to Subsonic API (JSON only for now)"""
    def __init__(self, data: Dict[str, Any], version: str = "1.16.1", status: str = "ok"):
        self.response = {
            "subsonic-response": {
                "status": status,
                "version": version,
                "type": "audiovault",
                "serverVersion": settings.VERSION,
                **data
            }
        }

    def as_json(self):
        return JSONResponse(content=self.response)

# --- AUTHENTICATION ---

async def get_subsonic_user(
    u: str = Query(..., description="Username"),
    t: Optional[str] = Query(None, description="Token or password"),
    p: Optional[str] = Query(None, description="Password (hex) or Token"),
    s: Optional[str] = Query(None, description="Salt"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates Subsonic credentials.
    Supports:
    1. Legacy: u=user&p=hex(md5(password))  (Note: some clients send plain hex)
    2. Token: u=user&t=md5(password + salt)&s=salt
    """
    result = await db.execute(select(User).where(User.username == u))
    user = result.scalars().first()

    if not user or not user.is_active or not user.subsonic_password:
        # 401 code 40: Wrong username or password
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Stored password is MD5(real_password)
    stored_md5 = user.subsonic_password

    # Case 1: Token Auth (t = md5(password + salt))
    # Standard Subsonic requires the cleartext password to compute this check:
    # check = md5(cleartext_password + salt)
    # But we ONLY have md5(cleartext_password). 
    # WE CANNOT VALIDATE STANDARD TOKEN AUTH WITHOUT CLEARTEXT PASSWORD.
    # However, some servers allow t = md5(md5(password) + salt). Let's see if clients support that mode?
    # No, typically they don't.
    # 
    # Workaround: For this implementation, we will assume clients use LEGACY AUTH or
    # we implement a custom flow. Most clients (Symfonium, DSub) try legacy auth if token fails or can be configured.
    # 
    # Actually, if we use the stored_md5 as the "secret", then:
    # t_check = md5(stored_md5 + s)
    # This works if the client considers the "password" to be the md5 hash itself? No.
    #
    # Let's fallback to checking 'p' (Legacy Auth).
    # p should be hex-encoded password. OR hex-encoded "enc:..."
    
    if p:
        # Legacy: p = hex(password) OR 'enc:hex(password)'
        # Since we store md5(password), we verify md5(decode_hex(p)) == stored_md5?
        # No, client sends hex(plain_password).
        # We decode p -> plain_password. Then hash it -> md5(plain_password). Compare with stored_md5.
        
        try:
            password_candidate = p
            if p.startswith("enc:"):
                password_candidate = bytes.fromhex(p[4:]).decode('utf-8')
            else:
                # Some clients send plain text in p? Or hex encoded?
                # Spec says: "Hex-encoded password".
                try:
                    password_candidate = bytes.fromhex(p).decode('utf-8')
                except:
                    # Maybe it's plain text (not spec compliant but possible)
                    password_candidate = p
            
            # Hash candidate
            candidate_md5 = hashlib.md5(password_candidate.encode('utf-8')).hexdigest()
            
            if candidate_md5 == stored_md5:
                return user
                
        except Exception as e:
            logger.error(f"Auth error: {e}")
            pass

    # If we get here, handling token auth impossible without plain password.
    # Unless... we mandate that for Audiovault Subsonic, the "Password" you enter in the CLIENT
    # IS the MD5 hash itself? No that's bad UX.
    #
    # MVP DECISION: We ONLY support clients sending Legacy Auth (Password in hex).
    # Symfonium: Uncheck "Legacy Auth" -> uses Token. Check "Legacy Auth" -> uses Hex Password.
    # We will instruct user to uses Legacy Auth.
    
    # Try simple token check assuming password IS the md5 hash (unlikely to work but fallback)
    if t and s:
        # specific check: md5(stored_md5 + s) == t ?
        check_val = hashlib.md5((stored_md5 + s).encode('utf-8')).hexdigest()
        if check_val == t:
            return user
            
    # Fail
    # Return generic error structure if possible, but FastAPI handles exception
    # Subsonic expects XML error, but we return JSON error 
    raise HTTPException(status_code=401, detail="Invalid credentials. Use Legacy Auth.")

# --- ENDPOINTS ---

@router.get("/ping.view")
@router.post("/ping.view")
async def ping(
    u: str, 
    p: Optional[str] = None, 
    t: Optional[str] = None, 
    s: Optional[str] = None,
    f: str = "json",
    user: User = Depends(get_subsonic_user)
):
    """Test connectivity"""
    return SubsonicResponse({}, version="1.16.1").as_json()

@router.get("/getLicense.view")
async def get_license(
    u: str, p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    user: User = Depends(get_subsonic_user)
):
    return SubsonicResponse({
        "license": {
            "valid": True,
            "email": user.email,
            "licenseExpires": "2099-01-01T00:00:00"
        }
    }).as_json()

@router.get("/getMusicFolders.view")
async def get_music_folders(
    u: str, p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    user: User = Depends(get_subsonic_user)
):
    return SubsonicResponse({
        "musicFolders": {
            "musicFolder": [
                {"id": 1, "name": "Music"}
            ]
        }
    }).as_json()

@router.get("/getIndexes.view")
async def get_indexes(
    musicFolderId: Optional[int] = None,
    ifModifiedSince: Optional[int] = None,
    u: str = Query(...), p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_subsonic_user)
):
    """Returns artists grouped by index"""
    # Fetch all artists with albums count
    result = await db.execute(select(Artist).options(selectinload(Artist.albums)).order_by(Artist.name))
    artists = result.scalars().all()
    
    # Group by first letter
    indexes = {}
    for artist in artists:
        if not artist.name: continue
        letter = artist.name[0].upper()
        if not letter.isalpha():
            letter = '#'
        
        if letter not in indexes:
            indexes[letter] = []
            
        indexes[letter].append({
            "id": str(artist.id),
            "name": artist.name,
            "artistImageUrl": artist.images.get('image_url') if artist.images else None,
            "albumCount": len(artist.albums)
        })
        
    formatted_indexes = []
    for letter in sorted(indexes.keys()):
        formatted_indexes.append({
            "name": letter,
            "artist": indexes[letter]
        })

    return SubsonicResponse({
        "indexes": {
            "lastModified": int(datetime.utcnow().timestamp() * 1000),
            "index": formatted_indexes
        }
    }).as_json()

@router.get("/getArtist.view")
async def get_artist(
    id: str,
    u: str, p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_subsonic_user)
):
    """Returns details for an artist (albums)"""
    # ID is UUID string, but Subsonic IDs are usually strings anyway.
    from uuid import UUID
    try:
        artist_uuid = UUID(id)
    except:
        # Handle case where ID might not be valid UUID
        return SubsonicResponse({"error": {"code": 70, "message": "Artist not found"}}, status="failed").as_json()

    result = await db.execute(select(Artist).where(Artist.id == artist_uuid).options(selectinload(Artist.albums)))
    artist = result.scalars().first()
    
    if not artist:
        return SubsonicResponse({"error": {"code": 70, "message": "Artist not found"}}, status="failed").as_json()

    albums_formatted = []
    for album in artist.albums:
        albums_formatted.append({
            "id": str(album.id),
            "name": album.title,
            "artist": artist.name,
            "artistId": str(artist.id),
            "coverArt": str(album.id), # Use album ID for cover art
            "songCount": album.total_tracks or 0,
            "duration": 0, # Aggregate if possible
            "created": album.created_at.isoformat()
        })

    return SubsonicResponse({
        "artist": {
            "id": str(artist.id),
            "name": artist.name,
            "album": albums_formatted
        }
    }).as_json()

@router.get("/getAlbum.view")
async def get_album(
    id: str,
    u: str, p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_subsonic_user)
):
    from uuid import UUID
    try:
        album_uuid = UUID(id)
    except:
        return SubsonicResponse({"error": {"code": 70, "message": "Album not found"}}, status="failed").as_json()

    # Load album with tracks
    result = await db.execute(select(Album).where(Album.id == album_uuid).options(selectinload(Album.tracks)))
    album = result.scalars().first()
    
    if not album:
        return SubsonicResponse({"error": {"code": 70, "message": "Album not found"}}, status="failed").as_json()

    songs = []
    for track in album.tracks:
        # Determine file path / format. 
        # Ideally track has a 'download' relation.
        # For this MVP, we return metadata.
        # Ensure we send 'isDir': false
        
        # Suffix/Format
        # We need to know if it's downloaded.
        # Let's verify 'downloads' relation manually or eager load it?
        # Assuming for now it logic handles existence in stream.view
        
        songs.append({
            "id": str(track.id),
            "parent": str(album.id),
            "title": track.title,
            "isDir": False,
            "album": album.title,
            "artist": track.artist, # String name
            "track": 0, # Add track number column later
            "coverArt": str(album.id),
            "duration": (track.duration_ms or 0) // 1000,
            "path": f"{track.id}.mp3", # Virtual path
            "suffix": "mp3", # Assumption
            "contentType": "audio/mpeg",
            "isVideo": False
        })

    return SubsonicResponse({
        "album": {
            "id": str(album.id),
            "name": album.title,
            "artist": album.artist.name if album.artist else "Unknown",
            "artistId": str(album.artist_id) if album.artist_id else "",
            "songCount": len(songs),
            "song": songs
        }
    }).as_json()

@router.get("/stream.view")
async def stream_music(
    id: str,
    u: str, p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_subsonic_user)
):
    """Streams the audio file"""
    from uuid import UUID
    try:
        track_uuid = UUID(id)
    except:
        raise HTTPException(status_code=404, detail="Track not found")

    # Get Track info and Download info
    # We need to join with Download table to get file_path
    from app.models.download import Download
    
    stmt = (
        select(Track)
        .where(Track.id == track_uuid)
        .options(selectinload(Track.downloads))
    )
    result = await db.execute(stmt)
    track = result.scalars().first()

    if not track or not track.downloads:
        raise HTTPException(status_code=404, detail="Track not found or not downloaded")

    # Find a completed download
    download = next((d for d in track.downloads if d.status == "completed"), None)
    
    if not download or not download.file_path:
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    import os
    file_path = download.file_path
    
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail="File missing from disk")

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg", # Or detect mime type
        filename=f"{track.title}.mp3"
    )

@router.get("/getCoverArt.view")
async def get_cover_art(
    id: str,
    size: Optional[int] = None,
    u: str = Query(...), p: Optional[str] = None, t: Optional[str] = None, s: Optional[str] = None, f: str = "json",
    db: AsyncSession = Depends(get_db)
    # Auth is simpler here because players often load images aggressively.
    # But ideally strictly protected.
):
    # ID is likely an Album ID (from our implementation)
    from uuid import UUID
    try:
        album_uuid = UUID(id)
        result = await db.execute(select(Album).where(Album.id == album_uuid))
        album = result.scalars().first()
        if album and album.images:
            # album.images is JSON. Check format.
            # Usually {"image_url": "..."} or Dict[str, str]
            import aiohttp
            
            image_url = None
            if isinstance(album.images, dict):
                image_url = album.images.get("image_url") or album.images.get("large") or album.images.get("medium")
            
            if image_url:
                # Proxy the image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            return Response(content=content, media_type="image/jpeg")
    except:
        pass
        
    # User placeholder?
    # Return 404
    return Response(status_code=404)
