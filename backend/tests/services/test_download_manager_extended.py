"""
Extended tests for DownloadManager to increase code coverage to 80%+.
Covers: file handling, playlist operations, error scenarios, URL resolution.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.download_manager import DownloadManager, DownloadPausedError


@pytest.fixture
def download_manager():
    dm = DownloadManager()
    return dm


@pytest.fixture
def mock_download():
    """Create a mock download with all necessary attributes."""
    download = MagicMock()
    download.id = uuid.uuid4()
    download.user_id = uuid.uuid4()
    download.track_id = uuid.uuid4()
    download.status = "pending"
    download.source = "spotify"
    download.playlist_name = "Test Playlist"
    download.file_path = "/tmp/test_song.mp3"
    download.progress = 0
    download.retry_count = 0
    download.error_message = None
    download.file_size = None
    download.created_at = datetime.now(UTC)

    # User mock
    download.user = MagicMock()
    download.user.id = download.user_id
    download.user.username = "testuser"
    download.user.preferences = {"quality": "high", "download_path": "/tmp/downloads"}

    # Track mock
    download.track = MagicMock()
    download.track.id = download.track_id
    download.track.title = "Test Song"
    download.track.artist = "Test Artist"
    download.track.album = "Test Album"
    download.track.metadata_content = {"image_url": "https://example.com/cover.jpg"}

    return download


# =============================================================================
# GRUPA 1: Obsługa zakończenia pobierania (_handle_completion)
# =============================================================================


@pytest.mark.asyncio
async def test_dm_handle_completion_with_mp3_format(download_manager, mock_download):
    """Test completion handler with MP3 format."""
    db_mock = AsyncMock()
    mock_download.file_path = "/tmp/test.mp3"
    container = {"path": "/tmp/test.mp3"}

    download_manager._target_format = "mp3"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=5000000),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
        patch(
            "app.services.library_scanner.library_scanner_service._parse_audio_metadata_sync",
            return_value=("Title MP3", "Artist MP3", "Album MP3", "Pop", 180000),
        ),
        patch(
            "app.services.library_scanner.library_scanner_service.resolve_artist_and_album",
            new_callable=AsyncMock,
            return_value=("artist_uuid", "album_uuid"),
        ),
    ):
        await download_manager._handle_completion(db_mock, mock_download, container, "template")

        assert mock_download.status == "completed"
        assert mock_download.progress == 100
        assert mock_download.file_size == 5000000
        assert mock_download.track.title == "Title MP3"
        assert mock_download.track.artist_id == "artist_uuid"


@pytest.mark.asyncio
async def test_dm_handle_completion_with_flac_format(download_manager, mock_download):
    """Test completion handler with FLAC lossless format."""
    db_mock = AsyncMock()
    mock_download.file_path = "/tmp/test.flac"
    container = {"path": "/tmp/test.flac"}

    download_manager._target_format = "flac"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=50000000),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
        patch(
            "app.services.library_scanner.library_scanner_service._parse_audio_metadata_sync",
            return_value=("Title FLAC", "Artist FLAC", "Album FLAC", "Classical", 300000),
        ),
        patch(
            "app.services.library_scanner.library_scanner_service.resolve_artist_and_album",
            new_callable=AsyncMock,
            return_value=("artist_id", "album_id"),
        ),
    ):
        await download_manager._handle_completion(db_mock, mock_download, container, "template")

        assert mock_download.status == "completed"
        assert mock_download.file_path.endswith(".flac")


@pytest.mark.asyncio
async def test_dm_handle_completion_missing_file(download_manager, mock_download):
    """Test completion when file doesn't exist."""
    db_mock = AsyncMock()
    container = {"path": None}

    with (
        patch("os.path.exists", return_value=False),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
    ):
        await download_manager._handle_completion(db_mock, mock_download, container, "template")

        assert mock_download.status == "completed"
        assert mock_download.file_size is None


@pytest.mark.asyncio
async def test_dm_handle_completion_with_playlist_update(download_manager, mock_download):
    """Test completion triggers playlist M3U update."""
    db_mock = AsyncMock()
    mock_download.playlist_name = "My Playlist"
    container = {"path": "/tmp/test.mp3"}

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=1000),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
        patch(
            "app.services.library_scanner.library_scanner_service._parse_audio_metadata_sync",
            return_value=("T", "A", "AL", None, 0),
        ),
        patch(
            "app.services.library_scanner.library_scanner_service.resolve_artist_and_album",
            new_callable=AsyncMock,
            return_value=(None, None),
        ),
        patch.object(download_manager, "update_playlist_m3u", new_callable=AsyncMock) as mock_update,
    ):
        await download_manager._handle_completion(db_mock, mock_download, container, "tmpl")

        mock_update.assert_called_once_with(db_mock, mock_download.user_id, "My Playlist")


# =============================================================================
# GRUPA 2: Zarządzanie ścieżkami plików
# =============================================================================


def test_dm_set_download_file_path_mp3(download_manager, mock_download):
    """Test setting file path with MP3 format."""
    container = {"path": "/tmp/music/song.webm"}

    download_manager._set_download_file_path(mock_download, container, "template", "mp3")

    assert mock_download.file_path == "/tmp/music/song.mp3"


def test_dm_set_download_file_path_flac(download_manager, mock_download):
    """Test setting file path with FLAC format."""
    container = {"path": "/tmp/music/song.webm"}

    download_manager._set_download_file_path(mock_download, container, "template", "flac")

    assert mock_download.file_path == "/tmp/music/song.flac"


def test_dm_set_download_file_path_no_container(download_manager, mock_download):
    """Test setting file path when container is empty (fallback logic)."""
    container = {"path": None}
    mock_download.user.preferences = {"downloadPath": None}

    with patch("os.path.exists", return_value=True), patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"

        download_manager._set_download_file_path(mock_download, container, "artist - title", "mp3")

        assert "/downloads" in mock_download.file_path or "/testuser" in mock_download.file_path


def test_dm_fix_filename_artifacts_na_prefix(download_manager, mock_download):
    """Test fixing NA - prefix in filename."""
    mock_download.file_path = "/tmp/NA - Test Song.mp3"

    with patch("os.path.exists", return_value=True), patch("os.rename") as mock_rename:
        download_manager._fix_filename_artifacts(mock_download)

        mock_rename.assert_called_once()
        # Check new path doesn't have "NA -"
        call_args = mock_rename.call_args[0]
        assert "NA -" not in call_args[1]


def test_dm_fix_filename_artifacts_uploader_prefix(download_manager, mock_download):
    """Test fixing uploader|creator - prefix in filename."""
    mock_download.file_path = "/tmp/uploader|creator - Real Title.mp3"

    with patch("os.path.exists", return_value=True), patch("os.rename") as mock_rename:
        download_manager._fix_filename_artifacts(mock_download)

        mock_rename.assert_called_once()
        call_args = mock_rename.call_args[0]
        assert "uploader" not in call_args[1].lower()


def test_dm_fix_filename_artifacts_no_change_needed(download_manager, mock_download):
    """Test that clean filenames are not modified."""
    mock_download.file_path = "/tmp/Artist - Song Title.mp3"

    with patch("os.path.exists", return_value=True), patch("os.rename") as mock_rename:
        download_manager._fix_filename_artifacts(mock_download)

        mock_rename.assert_not_called()


# =============================================================================
# GRUPA 3: Obsługa błędów (_handle_error)
# =============================================================================


@pytest.mark.asyncio
async def test_dm_handle_error_paused(download_manager, mock_download):
    """Test error handler correctly handles paused state."""
    db_mock = AsyncMock()
    error = DownloadPausedError("DOWNLOAD_PAUSED")

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager._handle_error(db_mock, mock_download, error)

        assert mock_download.status == "paused"
        mock_emit.assert_called_once()
        assert "download:paused" in str(mock_emit.call_args)


@pytest.mark.asyncio
async def test_dm_handle_error_generic(download_manager, mock_download):
    """Test error handler for generic exceptions."""
    db_mock = AsyncMock()
    error = Exception("Network timeout")
    mock_download.retry_count = 1

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager._handle_error(db_mock, mock_download, error)

        assert mock_download.status == "failed"
        assert mock_download.error_message == "Network timeout"
        assert mock_download.retry_count == 2
        mock_emit.assert_called_once()


# =============================================================================
# GRUPA 4: Operacje na playlistach
# =============================================================================


@pytest.mark.asyncio
async def test_dm_get_playlist_downloads(download_manager):
    """Test getting downloads for a playlist."""
    db_mock = AsyncMock()
    user_id = str(uuid.uuid4())

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
    db_mock.execute.return_value = mock_result

    result = await download_manager._get_playlist_downloads(db_mock, user_id, "spotify", "My Playlist")

    assert len(result) == 2


@pytest.mark.asyncio
async def test_dm_get_playlist_downloads_invalid_uuid(download_manager):
    """Test getting playlist downloads with invalid UUID."""
    db_mock = AsyncMock()

    result = await download_manager._get_playlist_downloads(db_mock, "invalid-uuid", "spotify", "Playlist")

    assert result == []


def test_dm_delete_physical_files(download_manager):
    """Test physical file deletion."""
    downloads = [
        MagicMock(id="dl1", file_path="/tmp/song1.mp3"),
        MagicMock(id="dl2", file_path="/tmp/song2.mp3"),
        MagicMock(id="dl3", file_path=None),
    ]

    with patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove:
        download_manager._delete_physical_files(downloads)

        assert mock_remove.call_count == 2


def test_dm_delete_physical_files_with_active_tasks(download_manager):
    """Test that active tasks are cancelled during deletion."""
    dl_id = "active_dl"
    mock_task = MagicMock()
    download_manager.active_tasks[dl_id] = mock_task

    downloads = [MagicMock(id=dl_id, file_path="/tmp/active.mp3")]

    with patch("os.path.exists", return_value=True), patch("os.remove"):
        download_manager._delete_physical_files(downloads)

        mock_task.cancel.assert_called_once()
        assert dl_id not in download_manager.active_tasks


def test_dm_cleanup_empty_directory(download_manager, mock_download):
    """Test cleanup of empty directories after playlist deletion."""
    downloads = [mock_download]
    mock_download.file_path = "/tmp/downloads/playlist_name/song.mp3"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
        patch("os.rmdir") as mock_rmdir,
        patch("os.path.dirname", side_effect=["/tmp/downloads/playlist_name", "/tmp/downloads"]),
    ):
        download_manager._cleanup_empty_directory(downloads, "playlist_name")

        # Should try to remove m3u8 and directory
        assert mock_remove.called or mock_rmdir.called


@pytest.mark.asyncio
async def test_dm_delete_db_records(download_manager):
    """Test deleting download records from database."""
    db_mock = AsyncMock()
    downloads = [MagicMock(id="dl1"), MagicMock(id="dl2")]

    await download_manager._delete_db_records(db_mock, downloads)

    assert db_mock.delete.call_count == 2
    db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_dm_delete_playlist_full_flow(download_manager):
    """Test full playlist deletion flow."""
    db_mock = AsyncMock()
    user_id = str(uuid.uuid4())

    mock_downloads = [MagicMock(file_path="/tmp/song.mp3")]

    with (
        patch.object(download_manager, "_get_playlist_downloads", new_callable=AsyncMock, return_value=mock_downloads),
        patch.object(download_manager, "_delete_physical_files"),
        patch.object(download_manager, "_cleanup_empty_directory"),
        patch.object(download_manager, "_delete_db_records", new_callable=AsyncMock),
    ):
        await download_manager.delete_playlist(db_mock, user_id, "spotify", "Test Playlist")


@pytest.mark.asyncio
async def test_dm_delete_playlist_empty(download_manager):
    """Test deletion when no downloads found."""
    db_mock = AsyncMock()

    with patch.object(download_manager, "_get_playlist_downloads", new_callable=AsyncMock, return_value=[]):
        await download_manager.delete_playlist(db_mock, "user", "spotify", "Empty Playlist")


# =============================================================================
# GRUPA 5: URL Resolution
# =============================================================================


@pytest.mark.asyncio
async def test_dm_resolve_url_youtube_search(download_manager, mock_download):
    """Test URL resolution for YouTube search."""
    db_mock = AsyncMock()
    mock_download.source = "spotify"
    mock_download.retry_count = 0

    mock_track = MagicMock()
    mock_track.title = "Song"
    mock_track.artist = "Artist"

    with (
        patch.object(download_manager, "get_track_info", new_callable=AsyncMock, return_value=mock_track),
        patch(
            "app.services.download_manager.fallback_service.get_fallback_instruction",
            return_value={"type": "yt_search", "value": "Artist - Song"},
        ),
    ):
        url = await download_manager._resolve_url(db_mock, mock_download)

        assert url.startswith("ytsearch1:")


@pytest.mark.asyncio
async def test_dm_resolve_url_soundcloud_search(download_manager, mock_download):
    """Test URL resolution for SoundCloud search."""
    db_mock = AsyncMock()
    mock_download.source = "soundcloud"

    with (
        patch.object(download_manager, "get_track_info", new_callable=AsyncMock, return_value=None),
        patch(
            "app.services.download_manager.fallback_service.get_fallback_instruction",
            return_value={"type": "sc_search", "value": "query"},
        ),
    ):
        url = await download_manager._resolve_url(db_mock, mock_download)

        assert url.startswith("scsearch1:")


@pytest.mark.asyncio
async def test_dm_resolve_url_direct_youtube(download_manager, mock_download):
    """Test direct YouTube URL resolution."""
    db_mock = AsyncMock()
    mock_download.track_id = "dQw4w9WgXcQ"

    with (
        patch.object(download_manager, "get_track_info", new_callable=AsyncMock, return_value=None),
        patch(
            "app.services.download_manager.fallback_service.get_fallback_instruction",
            return_value={"type": "direct_youtube", "value": None},
        ),
    ):
        url = await download_manager._resolve_url(db_mock, mock_download)

        assert "youtube.com/watch" in url


@pytest.mark.asyncio
async def test_dm_resolve_url_none_fallback(download_manager, mock_download):
    """Test fallback when no URL can be resolved."""
    db_mock = AsyncMock()

    with (
        patch.object(download_manager, "get_track_info", new_callable=AsyncMock, return_value=None),
        patch(
            "app.services.download_manager.fallback_service.get_fallback_instruction",
            return_value={"type": "none", "value": None},
        ),
    ):
        url = await download_manager._resolve_url(db_mock, mock_download)

        assert url == ""


# =============================================================================
# GRUPA 6: Progress & Queue Management
# =============================================================================


@pytest.mark.asyncio
async def test_dm_update_progress_db(download_manager):
    """Test progress update in database."""
    download_id = str(uuid.uuid4())

    with patch("app.services.download_manager.AsyncSessionLocal") as mock_session:
        db_mock = AsyncMock()
        mock_session.return_value.__aenter__.return_value = db_mock

        mock_result = MagicMock()
        mock_download = MagicMock(progress=0)
        mock_result.scalar_one_or_none.return_value = mock_download
        db_mock.execute.return_value = mock_result

        await download_manager.update_progress_db(download_id, 50.0)

        assert mock_download.progress == pytest.approx(50.0)
        db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_dm_resume_pending_downloads(download_manager):
    """Test resuming pending downloads on startup."""
    db_mock = AsyncMock()

    mock_downloads = [
        MagicMock(id=uuid.uuid4(), status="downloading", progress=50),
        MagicMock(id=uuid.uuid4(), status="pending", progress=0),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_downloads
    db_mock.execute.return_value = mock_result

    with patch.object(download_manager, "start_worker", new_callable=AsyncMock):
        await download_manager.resume_pending_downloads(db_mock)

        # First download should be reset
        assert mock_downloads[0].status == "pending"
        assert mock_downloads[0].progress == 0
        assert download_manager.queue.qsize() == 2


@pytest.mark.asyncio
async def test_dm_resume_pending_no_downloads(download_manager):
    """Test resume when no pending downloads exist."""
    db_mock = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db_mock.execute.return_value = mock_result

    await download_manager.resume_pending_downloads(db_mock)

    assert download_manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_dm_retry_failed_downloads(download_manager):
    """Test retrying failed downloads."""
    db_mock = AsyncMock()

    mock_downloads = [
        MagicMock(id=uuid.uuid4(), status="failed", retry_count=1),
        MagicMock(id=uuid.uuid4(), status="failed", retry_count=None),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_downloads
    db_mock.execute.return_value = mock_result

    with patch.object(download_manager, "start_worker", new_callable=AsyncMock):
        await download_manager.retry_failed_downloads(db_mock)

        assert all(d.status == "pending" for d in mock_downloads)
        assert download_manager.queue.qsize() == 2


# =============================================================================
# GRUPA 7: YDL Options generation
# =============================================================================


def test_dm_get_ydl_options_high_quality(download_manager, mock_download):
    """Test YDL options for high quality MP3."""
    mock_download.user.preferences = {"quality": "high", "filename_schema": "{artist} - {title}"}

    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"

        ydl_opts, _ = download_manager._get_ydl_options(mock_download, lambda x: None)

        assert ydl_opts["format"] == "bestaudio/best"
        assert any(
            pp.get("preferredquality") == "320"
            for pp in ydl_opts["postprocessors"]
            if pp.get("key") == "FFmpegExtractAudio"
        )


def test_dm_get_ydl_options_lossless(download_manager, mock_download):
    """Test YDL options for lossless FLAC."""
    mock_download.user.preferences = {"quality": "lossless", "filename_schema": "{artist} - {title}"}

    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"

        ydl_opts, _ = download_manager._get_ydl_options(mock_download, lambda x: None)

        assert any(
            pp.get("preferredcodec") == "flac"
            for pp in ydl_opts["postprocessors"]
            if pp.get("key") == "FFmpegExtractAudio"
        )
        assert download_manager._target_format == "flac"


def test_dm_get_ydl_options_with_playlist_tag(download_manager, mock_download):
    """Test YDL options with playlist tag in schema."""
    mock_download.user.preferences = {"quality": "high", "filename_schema": "{playlist}/{artist} - {title}"}
    mock_download.playlist_name = "My Awesome Playlist"

    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "/downloads"

        ydl_opts, _ = download_manager._get_ydl_options(mock_download, lambda x: None)

        assert "My Awesome Playlist" in ydl_opts["outtmpl"] or "My_Awesome_Playlist" in ydl_opts["outtmpl"]


# =============================================================================
# GRUPA 8: M3U Playlist Generation
# =============================================================================


@pytest.mark.asyncio
async def test_dm_update_playlist_m3u(download_manager):
    """Test M3U playlist file generation."""
    db_mock = AsyncMock()
    user_id = str(uuid.uuid4())

    mock_downloads = [
        MagicMock(
            file_path="/tmp/downloads/song1.mp3",
            track=MagicMock(artist="Artist1", title="Song1"),
            user=MagicMock(username="testuser", preferences={}),
        ),
        MagicMock(
            file_path="/tmp/downloads/song2.mp3",
            track=MagicMock(artist="Artist2", title="Song2"),
            user=MagicMock(username="testuser", preferences={}),
        ),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_downloads
    db_mock.execute.return_value = mock_result

    with (
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
    ):
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Mock the playlist DB sync part
        with patch("app.models.playlist.Playlist"), patch("app.models.playlist.PlaylistTrack"):
            await download_manager.update_playlist_m3u(db_mock, user_id, "Test Playlist")


@pytest.mark.asyncio
async def test_dm_update_playlist_m3u_empty(download_manager):
    """Test M3U generation with no downloads."""
    db_mock = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db_mock.execute.return_value = mock_result

    # Should return early without error
    await download_manager.update_playlist_m3u(db_mock, "user_id", "Empty Playlist")


# =============================================================================
# GRUPA 9: Process queue and semaphore handling
# =============================================================================


@pytest.mark.asyncio
async def test_dm_process_with_semaphore_invalid_uuid(download_manager):
    """Test semaphore processing with invalid download ID."""
    await download_manager.queue.put("invalid-uuid")

    # Should handle gracefully and mark task done
    await download_manager._process_with_semaphore("invalid-uuid")

    # Queue should be empty after processing
    assert download_manager.queue.empty()


@pytest.mark.asyncio
async def test_dm_process_with_semaphore_download_not_found(download_manager):
    """Test semaphore processing when download not found in DB."""
    download_id = str(uuid.uuid4())

    # Add item to queue first so task_done() doesn't fail
    await download_manager.queue.put(download_id)

    with patch("app.services.download_manager.AsyncSessionLocal") as mock_session:
        db_mock = AsyncMock()
        mock_session.return_value.__aenter__.return_value = db_mock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_result

        await download_manager._process_with_semaphore(download_id)


# =============================================================================
# GRUPA 10: Permissions and file system operations
# =============================================================================


def test_dm_ensure_permissions_file(download_manager):
    """Test setting file permissions."""
    with patch("os.chmod") as mock_chmod:
        download_manager._ensure_permissions("/tmp/test.mp3", is_file=True)
        mock_chmod.assert_called_once_with("/tmp/test.mp3", 0o666)


def test_dm_ensure_permissions_directory(download_manager):
    """Test setting directory permissions."""
    with patch("os.chmod") as mock_chmod:
        download_manager._ensure_permissions("/tmp/music", is_file=False)
        mock_chmod.assert_called_once_with("/tmp/music", 0o777)


def test_dm_ensure_permissions_error(download_manager):
    """Test graceful handling of permission errors."""
    with patch("os.chmod", side_effect=PermissionError("Access denied")):
        # Should not raise, just log
        download_manager._ensure_permissions("/tmp/readonly", is_file=False)


# =============================================================================
# GRUPA 11: Execute download task & caching
# =============================================================================


@pytest.mark.asyncio
async def test_dm_execute_download_cache_miss_with_entries(download_manager):
    """Test download execution with cache miss and search results."""
    loop = asyncio.get_event_loop()
    ydl_opts = {"quiet": True}
    url = "ytsearch1:test query"
    download_id = str(uuid.uuid4())

    with (
        patch("app.services.download_manager.cache_manager.get", new_callable=AsyncMock, return_value=None) as mock_get,
        patch("app.services.download_manager.cache_manager.set", new_callable=AsyncMock) as mock_set,
        patch("yt_dlp.YoutubeDL") as mock_ydl,
    ):
        # Mock extract_info returning entries
        mock_info = {"entries": [{"webpage_url": "https://youtube.com/watch?v=resolved"}]}

        with patch.object(loop, "run_in_executor", new_callable=AsyncMock, return_value=mock_info):
            mock_ydl_instance = MagicMock()
            mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl.return_value.download = MagicMock()

            await download_manager._execute_download_task(loop, ydl_opts, url, download_id)

            # Should cache the resolved URL
            mock_set.assert_called()
            mock_get.assert_called()


@pytest.mark.asyncio
async def test_dm_execute_download_cache_hit(download_manager):
    """Test download execution with cache hit."""
    loop = asyncio.get_event_loop()
    ydl_opts = {"quiet": True}
    url = "ytsearch1:cached query"
    download_id = str(uuid.uuid4())

    with (
        patch(
            "app.services.download_manager.cache_manager.get", new_callable=AsyncMock, return_value="https://cached.url"
        ) as mock_get,
        patch("yt_dlp.YoutubeDL") as mock_ydl,
    ):
        mock_ydl_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

        with patch.object(loop, "run_in_executor", new_callable=AsyncMock):
            await download_manager._execute_download_task(loop, ydl_opts, url, download_id)

        mock_get.assert_called_once()


# =============================================================================
# GRUPA 12: Notify methods
# =============================================================================


@pytest.mark.asyncio
async def test_dm_notify_start(download_manager, mock_download):
    """Test download start notification."""
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager._notify_start(mock_download)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "download:progress"
        assert call_args[0][1]["status"] == "downloading"


@pytest.mark.asyncio
async def test_dm_notify_completion(download_manager, mock_download):
    """Test download completion notification."""
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager._notify_completion(mock_download)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "download:completed"


@pytest.mark.asyncio
async def test_dm_notify_processing(download_manager, mock_download):
    """Test processing status notification."""
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager._notify_processing(mock_download)

        mock_emit.assert_called_once()
        assert mock_emit.call_args[0][0] == "download:processing"
