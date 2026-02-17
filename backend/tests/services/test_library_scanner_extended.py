"""
Extended tests for LibraryScannerService to increase code coverage.
Covers: path validation, metadata parsing, scan operations, playlist imports.
"""

import os
import uuid
from typing import Any, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.library_scanner import UNKNOWN_ALBUM, UNKNOWN_ARTIST, LibraryScannerService


@pytest.fixture
def scanner():
    with patch("app.services.library_scanner.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"
        return LibraryScannerService()


# =============================================================================
# Path Validation
# =============================================================================


def test_validate_scan_path_none(scanner):
    """Test validation with no path returns base dir."""
    result = scanner._validate_scan_path(None)
    assert result == scanner.base_dir


def test_validate_scan_path_valid():
    """Test validation with valid subdirectory."""
    with patch("app.services.library_scanner.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"
        scanner = LibraryScannerService()

        result = scanner._validate_scan_path("/downloads/music")
        assert "downloads" in result


def test_validate_scan_path_outside_base():
    """Test validation denies paths outside base directory."""
    with patch("app.services.library_scanner.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"
        scanner = LibraryScannerService()

        with pytest.raises(ValueError, match="Access denied"):
            scanner._validate_scan_path("/etc/passwd")


def test_validate_scan_path_different_drive():
    """Test validation handles different drives (Windows)."""
    with patch("app.services.library_scanner.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "C:/downloads"
        scanner = LibraryScannerService()

        with pytest.raises(ValueError, match="Access denied"):
            scanner._validate_scan_path("D:/other")


# =============================================================================
# Default Metadata
# =============================================================================


def test_get_default_metadata(scanner):
    """Test default metadata generation."""
    title, artist, album, genre = scanner._get_default_metadata("Song.mp3")

    assert title == "Song"
    assert artist == UNKNOWN_ARTIST
    assert album == UNKNOWN_ALBUM
    assert genre is None


def test_get_default_metadata_complex_name(scanner):
    """Test default metadata with complex filename."""
    title, _, _, _ = scanner._get_default_metadata("Artist - Track Name.flac")

    assert title == "Artist - Track Name"


# =============================================================================
# EasyID3 Parsing
# =============================================================================


def test_try_parse_easyid3_success(scanner):
    """Test EasyID3 parsing with valid tags."""
    with patch("app.services.library_scanner.EasyID3") as mock_id3:
        mock_audio = {"title": ["Test Title"], "artist": ["Test Artist"], "album": ["Test Album"], "genre": ["Rock"]}
        mock_id3.return_value = mock_audio

        title, artist, album, genre = scanner._try_parse_easyid3("/tmp/test.mp3")

        assert title == "Test Title"
        assert artist == "Test Artist"
        assert album == "Test Album"
        assert genre == "Rock"


def test_try_parse_easyid3_no_tags(scanner):
    """Test EasyID3 parsing when no tags present."""
    with patch("app.services.library_scanner.EasyID3") as mock_id3:
        mock_id3.return_value = {}

        title, artist, _, _ = scanner._try_parse_easyid3("/tmp/default.mp3")

        # Should use defaults from filename
        assert "default" in title
        assert artist == UNKNOWN_ARTIST


def test_try_parse_easyid3_error(scanner):
    """Test EasyID3 graceful error handling."""
    with patch("app.services.library_scanner.EasyID3", side_effect=Exception("Parse error")):
        _, artist, _, _ = scanner._try_parse_easyid3("/tmp/broken.mp3")

        # Should fall back to defaults
        assert artist == UNKNOWN_ARTIST


# =============================================================================
# Mutagen Fallback Parsing
# =============================================================================


def test_try_parse_mutagen_fallback(scanner):
    """Test Mutagen fallback parsing."""
    with patch("app.services.library_scanner.MutagenFile") as mock_mutagen:
        mock_file = MagicMock()
        mock_file.info.length = 180.5
        mock_file.__contains__ = lambda self, x: x in ["TPE1", "TIT2"]
        mock_file.__getitem__ = lambda self, x: {"TPE1": "Mutagen Artist", "TIT2": "Mutagen Title"}[x]
        mock_mutagen.return_value = mock_file

        current_meta = ("default", UNKNOWN_ARTIST, UNKNOWN_ALBUM, None)
        _, _, _, _, duration, _ = scanner._try_parse_mutagen_fallback("/tmp/test.mp3", current_meta)

        assert duration == 180500  # 180.5 * 1000


def test_try_parse_mutagen_fallback_no_info(scanner):
    """Test Mutagen fallback with no audio info."""
    with patch("app.services.library_scanner.MutagenFile", return_value=None):
        current_meta = ("title", "artist", "album", "genre")
        title, _, _, _, duration, _ = scanner._try_parse_mutagen_fallback("/tmp/test.mp3", current_meta)

        assert title == "title"
        assert duration == 0


def test_try_parse_mutagen_fallback_error(scanner):
    """Test Mutagen fallback error handling."""
    with patch("app.services.library_scanner.MutagenFile", side_effect=Exception("Error")):
        current_meta = ("title", "artist", "album", None)
        result = scanner._try_parse_mutagen_fallback("/tmp/test.mp3", current_meta)

        assert result[0] == "title"  # Should preserve input


# =============================================================================
# Source Inference
# =============================================================================


def test_infer_source_info_spotify_playlist(scanner):
    """Test source inference for Spotify playlist structure."""
    source, playlist = scanner._infer_source_info("/downloads/spotify/My Playlist/song.mp3", "/downloads")

    assert source == "spotify"
    assert playlist == "My Playlist"


def test_infer_source_info_youtube(scanner):
    """Test source inference for YouTube structure."""
    source, playlist = scanner._infer_source_info("/downloads/youtube/song.mp3", "/downloads")

    assert source == "youtube"
    assert playlist == "Uncategorized"


def test_infer_source_info_unknown_folder(scanner):
    """Test source inference for unknown folder structure."""
    _, playlist = scanner._infer_source_info("/downloads/CustomFolder/song.mp3", "/downloads")

    # Should treat as playlist name, not source
    assert playlist == "CustomFolder"


def test_infer_source_info_root_file(scanner):
    """Test source inference for file in root."""
    source, playlist = scanner._infer_source_info("/downloads/song.mp3", "/downloads")

    assert source == "local_import"
    assert playlist == "Imported"


# =============================================================================
# Resolve Artist and Album
# =============================================================================


@pytest.mark.asyncio
async def test_resolve_artist_and_album_existing(scanner):
    """Test resolving existing artist and album."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()

    mock_artist = MagicMock()
    mock_artist.id = uuid.uuid4()
    mock_album = MagicMock()
    mock_album.id = uuid.uuid4()

    # First query returns artist, second returns album
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = mock_artist
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = mock_album

    db_mock.execute.side_effect = [mock_result1, mock_result2]

    artist_id, album_id = await scanner.resolve_artist_and_album(db_mock, "Artist", "Album")

    assert artist_id == mock_artist.id
    assert album_id == mock_album.id


@pytest.mark.asyncio
async def test_resolve_artist_and_album_create_new(scanner):
    """Test creating new artist and album."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.flush = AsyncMock()

    # Both queries return None (nothing exists)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result

    _, _ = await scanner.resolve_artist_and_album(db_mock, "New Artist", "New Album")

    # Should have added new entities
    assert db_mock.add.call_count >= 2
    assert db_mock.flush.call_count >= 2


@pytest.mark.asyncio
async def test_resolve_artist_and_album_empty_names(scanner):
    """Test resolving with empty names defaults to Unknown."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.flush = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result

    await scanner.resolve_artist_and_album(db_mock, "", "")

    # Should create with Unknown Artist/Album
    assert db_mock.add.called


# =============================================================================
# Scan Directory
# =============================================================================


@pytest.mark.asyncio
async def test_scan_directory_nonexistent(scanner):
    """Test scanning non-existent directory."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    with patch("os.path.exists", return_value=False):
        result = await scanner.scan_directory(db_mock, "user123", "/downloads/missing")

    assert result["status"] == "error"
    assert "does not exist" in result["message"]


@pytest.mark.asyncio
async def test_scan_directory_access_denied(scanner):
    """Test scanning directory outside allowed path."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    result = await scanner.scan_directory(db_mock, "user123", "/etc/passwd")

    assert result["status"] == "error"
    assert "Access denied" in result["message"]


@pytest.mark.asyncio
async def test_scan_directory_empty(scanner):
    """Test scanning empty directory."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    db_mock.execute.return_value = mock_result

    with patch("os.path.exists", return_value=True), patch("os.walk", return_value=[]):
        result = await scanner.scan_directory(db_mock, str(uuid.uuid4()), scanner.base_dir)

    assert result["status"] == "success"
    assert result["imported_count"] == 0


@pytest.mark.asyncio
async def test_scan_directory_with_files(scanner):
    """Test scanning directory with MP3 files."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    db_mock.execute.return_value = mock_result

    files_list: list[tuple[str, list[str], list[str]]] = [(scanner.base_dir, [], ["song1.mp3", "song2.mp3", "readme.txt"])]

    with (
        patch("os.path.exists", return_value=True),
        patch("os.walk", return_value=files_list),
        patch.object(scanner, "_handle_scan_file", new_callable=AsyncMock, return_value=True),
    ):
        result = await scanner.scan_directory(db_mock, str(uuid.uuid4()), scanner.base_dir)

    assert result["status"] == "success"
    assert result["total_files_found"] == 2


# =============================================================================
# Get Known Paths
# =============================================================================


@pytest.mark.asyncio
async def test_get_known_paths(scanner):
    """Test getting known paths for user."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = [
        ("/downloads/song1.mp3",),
        ("/downloads/song2.mp3",),
        (None,),  # Should handle None paths
    ]
    db_mock.execute.return_value = mock_result

    paths = await scanner._get_known_paths(db_mock, str(uuid.uuid4()))

    assert len(paths) == 2


@pytest.mark.asyncio
async def test_get_known_paths_invalid_uuid(scanner):
    """Test known paths with invalid user ID."""
    db_mock = MagicMock()

    paths = await scanner._get_known_paths(db_mock, "invalid-uuid")

    assert paths == set()


# =============================================================================
# Handle Scan File
# =============================================================================


@pytest.mark.asyncio
async def test_handle_scan_file_playlist(scanner):
    """Test handling M3U playlist file."""
    db_mock = MagicMock()

    with patch.object(scanner, "_import_playlist", new_callable=AsyncMock):
        result = await scanner._handle_scan_file(
            db_mock, "user", "/downloads/playlist.m3u8", "playlist.m3u8", "/downloads", set()
        )

    assert result is False  # Playlists don't count as imported tracks


@pytest.mark.asyncio
async def test_handle_scan_file_non_mp3(scanner):
    """Test handling non-MP3 audio file."""
    db_mock = MagicMock()

    result = await scanner._handle_scan_file(db_mock, "user", "/downloads/song.wav", "song.wav", "/downloads", set())

    assert result is False


@pytest.mark.asyncio
async def test_handle_scan_file_already_known(scanner):
    """Test handling already imported file."""
    db_mock = MagicMock()
    known = {os.path.normpath("/downloads/known.mp3")}

    result = await scanner._handle_scan_file(db_mock, "user", "/downloads/known.mp3", "known.mp3", "/downloads", known)

    assert result is False


@pytest.mark.asyncio
async def test_handle_scan_file_new_mp3(scanner):
    """Test handling new MP3 file."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    with patch.object(scanner, "_process_audio_file", new_callable=AsyncMock):
        result = await scanner._handle_scan_file(db_mock, "user", "/downloads/new.mp3", "new.mp3", "/downloads", set())

    assert result is True


# =============================================================================
# Cleanup Orphans
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_orphans_none(scanner):
    """Test cleanup when no orphans exist."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db_mock.execute.return_value = mock_result

    count = await scanner.cleanup_orphans(db_mock)

    assert count == 0


@pytest.mark.asyncio
async def test_cleanup_orphans_with_orphans(scanner):
    """Test cleanup removes orphaned records."""
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.delete = AsyncMock()

    orphan = MagicMock()
    orphan.file_path = "/downloads/missing.mp3"
    orphan.track_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orphan]
    db_mock.execute.return_value = mock_result

    with patch("os.path.exists", return_value=False):
        count = await scanner.cleanup_orphans(db_mock)

    assert count == 1
    db_mock.delete.assert_called_once()
    db_mock.commit.assert_called_once()


# =============================================================================
# Update Meta From Tags
# =============================================================================


def test_update_meta_from_tags(scanner):
    """Test updating metadata from ID3 tags."""
    m = MagicMock()
    m.__contains__ = lambda self, x: x in ["TPE1", "TIT2", "TALB", "TCON"]
    m.__getitem__ = lambda self, x: {"TPE1": "Tag Artist", "TIT2": "Tag Title", "TALB": "Tag Album", "TCON": "Pop"}[x]

    current = ("filename", UNKNOWN_ARTIST, UNKNOWN_ALBUM, None)
    title, artist, album, genre = scanner._update_meta_from_tags(m, current, "filename.mp3")

    assert artist == "Tag Artist"
    assert title == "Tag Title"
    assert album == "Tag Album"
    assert genre == "Pop"


def test_update_meta_from_tags_partial(scanner):
    """Test updating with partial tags."""
    m = MagicMock()
    m.__contains__ = lambda self, x: x == "TPE1"
    m.__getitem__ = lambda self, x: "Only Artist"

    current = ("My Title", UNKNOWN_ARTIST, UNKNOWN_ALBUM, "Rock")
    title, artist, album, genre = scanner._update_meta_from_tags(m, current, "file.mp3")

    assert artist == "Only Artist"
    assert title == "My Title"  # Unchanged
    assert album == UNKNOWN_ALBUM  # Unchanged
    assert genre == "Rock"  # Unchanged
