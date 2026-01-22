import pytest
import os
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import select
from app.services.library_scanner import LibraryScannerService
from app.models.download import Download
from app.models.track import Track
from app.models.artist import Artist
from app.models.album import Album

@pytest.fixture
def scanner():
    return LibraryScannerService()

def test_validate_scan_path_valid(scanner):
    scanner.base_dir = os.path.abspath("/music")
    with patch("os.path.exists", return_value=True):
        result = scanner._validate_scan_path(os.path.abspath("/music/subdir"))
        assert result == os.path.abspath("/music/subdir")

def test_validate_scan_path_invalid(scanner):
    scanner.base_dir = os.path.abspath("/music")
    with pytest.raises(ValueError, match="Access denied"):
        scanner._validate_scan_path(os.path.abspath("/outside"))

def test_validate_scan_path_none(scanner):
    scanner.base_dir = os.path.abspath("/music")
    result = scanner._validate_scan_path(None)
    assert result == scanner.base_dir

def test_get_default_metadata(scanner):
    title, artist, album, genre = scanner._get_default_metadata("Test Song.mp3")
    assert title == "Test Song"
    assert artist == "Unknown Artist"
    assert album == "Unknown Album"
    assert genre is None

def test_infer_source_info_spotify(scanner):
    base_dir = "/music"
    file_path = "/music/spotify/My Playlist/song.mp3"
    source, playlist_name = scanner._infer_source_info(file_path, base_dir)
    assert source == "spotify"
    assert playlist_name == "My Playlist"

def test_infer_source_info_local(scanner):
    base_dir = "/music"
    file_path = "/music/My Album/song.mp3"
    _, playlist_name = scanner._infer_source_info(file_path, base_dir)
    assert playlist_name == "My Album"

def test_parse_audio_metadata_sync_no_tags(scanner):
    with patch("app.services.library_scanner.MutagenFile", return_value=None):
        title, artist, album, _, duration = scanner._parse_audio_metadata_sync("/fake/song.mp3")
        assert title == "song"
        assert artist == "Unknown Artist"
        assert album == "Unknown Album"
        assert duration == 0

@pytest.mark.asyncio
async def test_get_known_paths(scanner, db_session, admin_user):
    file_path = "/music/known.mp3"
    track = Track(id=uuid.uuid4(), title="Known Track")
    db_session.add(track)
    await db_session.flush()
    
    dl = Download(user_id=admin_user.id, track_id=track.id, file_path=file_path, status="completed")
    db_session.add(dl)
    await db_session.commit()
    
    paths = await scanner._get_known_paths(db_session, admin_user.id)
    assert os.path.normpath(file_path) in paths

@pytest.mark.asyncio
async def test_resolve_artist_and_album_new(scanner, db_session):
    artist_id, album_id = await scanner.resolve_artist_and_album(db_session, "New Artist", "New Album")
    assert artist_id is not None
    assert album_id is not None

@pytest.mark.asyncio
async def test_resolve_artist_and_album_existing(scanner, db_session):
    artist = Artist(id=uuid.uuid4(), name="Existing Artist")
    db_session.add(artist)
    await db_session.flush()
    
    album = Album(id=uuid.uuid4(), title="Existing Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.commit()
    
    artist_id, album_id = await scanner.resolve_artist_and_album(db_session, "Existing Artist", "Existing Album")
    assert artist_id == artist.id
    assert album_id == album.id

@pytest.mark.asyncio
async def test_scan_directory_nonexistent(scanner, db_session, admin_user):
    with patch("os.path.exists", return_value=False):
        result = await scanner.scan_directory(db_session, str(admin_user.id), "/nonexistent/path")
        assert result["status"] == "error"

@pytest.mark.asyncio
async def test_scan_directory_empty(scanner, db_session, admin_user):
    scanner.base_dir = os.path.abspath("/music")
    with patch("os.path.exists", return_value=True), \
         patch("os.walk", return_value=[(os.path.abspath("/music"), [], [])]):
        result = await scanner.scan_directory(db_session, str(admin_user.id), os.path.abspath("/music"))
        assert result["status"] == "success"
        assert result["imported_count"] == 0

@pytest.mark.asyncio
async def test_scan_directory_with_mp3(scanner, db_session, admin_user):
    scanner.base_dir = os.path.abspath("/music")
    with patch("os.path.exists", return_value=True), \
         patch("os.walk", return_value=[(os.path.abspath("/music"), [], ["test.mp3"])]), \
         patch("mutagen.File", return_value=None):
        result = await scanner.scan_directory(db_session, str(admin_user.id), os.path.abspath("/music"))
        assert result["status"] == "success"
        assert result["total_files_found"] >= 1

@pytest.mark.asyncio
async def test_handle_scan_file_non_audio(scanner, db_session, admin_user):
    result = await scanner._handle_scan_file(db_session, str(admin_user.id), "/music/readme.txt", "readme.txt", "/music", set())
    assert result is False

@pytest.mark.asyncio
async def test_handle_scan_file_already_known(scanner, db_session, admin_user):
    file_path = "/music/known.mp3"
    known_paths = {os.path.normpath(file_path)}
    result = await scanner._handle_scan_file(db_session, str(admin_user.id), file_path, "known.mp3", "/music", known_paths)
    assert result is False
@pytest.mark.asyncio
async def test_parse_audio_metadata_with_easyid3(scanner):
    mock_audio = {"title": ["Tagged Title"], "artist": ["Tagged Artist"], "album": ["Tagged Album"], "genre": ["Rock"]}
    with patch("app.services.library_scanner.EasyID3", return_value=mock_audio):
        # We need to also patch MutagenFile (local alias) for the duration/fallback
        mock_mutagen = MagicMock()
        mock_mutagen.info.length = 120.5
        mock_mutagen.__getitem__.side_effect = KeyError("No tags")
        with patch("app.services.library_scanner.MutagenFile", return_value=mock_mutagen):
             title, artist, _, _, duration = scanner._parse_audio_metadata_sync("/fake/song.mp3")
             assert title == "Tagged Title"
             assert artist == "Tagged Artist"
             assert duration == 120500

@pytest.mark.asyncio
async def test_cleanup_orphans(scanner, db_session):
    # 1. Create track-download pair with non-existent file path
    artist = Artist(id=uuid.uuid4(), name="Orphan Artist")
    db_session.add(artist)
    await db_session.flush()
    
    track = Track(id=uuid.uuid4(), title="Orphan Track", artist_id=artist.id)
    db_session.add(track)
    await db_session.flush()
    
    dl = Download(id=uuid.uuid4(), track_id=track.id, user_id=uuid.uuid4(), file_path="/non/existent/orphan.mp3", status="completed")
    db_session.add(dl)
    await db_session.commit()
    
    with patch("os.path.exists", return_value=False):
        removed = await scanner.cleanup_orphans(db_session)
        assert removed >= 1

@pytest.mark.asyncio
async def test_scan_directory_with_subdirs(scanner, db_session, admin_user):
    scanner.base_dir = os.path.abspath("/music")
    # Mock os.walk with nested structure
    walk_data = [
        (os.path.abspath("/music"), ["subdir"], ["root.mp3"]),
        (os.path.abspath("/music/subdir"), [], ["nested.mp3"])
    ]
    with patch("os.path.exists", return_value=True), \
         patch("os.walk", return_value=walk_data), \
         patch("app.services.library_scanner.MutagenFile", return_value=None), \
         patch.object(scanner, "_handle_scan_file", new_callable=AsyncMock, return_value=True):
        
        result = await scanner.scan_directory(db_session, str(admin_user.id), os.path.abspath("/music"))
        assert result["status"] == "success"
        assert result["imported_count"] == 2
