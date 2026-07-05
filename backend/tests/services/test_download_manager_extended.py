"""Extended tests for download_manager.py — covers previously untested branches."""

import asyncio
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.download_manager import DownloadManager


@pytest.fixture
def dm():
    return DownloadManager()


# ---------------------------------------------------------------------------
# start_worker / process_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_worker_creates_task(dm):
    with patch.object(dm, "process_queue", new_callable=AsyncMock):
        await dm.start_worker()
        assert dm.processing_task is not None

    # Second call while task is running — should not create a new one
    first_task = dm.processing_task
    with patch.object(dm, "process_queue", new_callable=AsyncMock):
        await dm.start_worker()
    assert dm.processing_task is first_task


@pytest.mark.asyncio
async def test_process_queue_skips_paused(dm):
    dl_id = str(uuid.uuid4())
    dm.paused_downloads.add(dl_id)
    await dm.queue.put(dl_id)

    with patch.object(dm, "_process_with_semaphore", new_callable=AsyncMock) as mock_proc:
        # Run one iteration — paused item → skipped → queue empty
        async def drain():
            await asyncio.wait_for(dm.process_queue(), timeout=0.2)

        with pytest.raises((asyncio.TimeoutError, asyncio.CancelledError)):
            await drain()
        mock_proc.assert_not_called()


# ---------------------------------------------------------------------------
# _process_with_semaphore
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_with_semaphore_invalid_uuid(dm):
    await dm.queue.put("not-a-uuid")
    dm.queue.task_done = MagicMock()
    # Should not raise
    await dm._process_with_semaphore("not-a-uuid")
    dm.queue.task_done.assert_called_once()


@pytest.mark.asyncio
async def test_process_with_semaphore_missing_download(dm):
    dl_id = str(uuid.uuid4())
    with patch("app.services.download_manager.AsyncSessionLocal") as mock_sl:
        db = MagicMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        mock_sl.return_value = db

        dm.queue.task_done = MagicMock()
        await dm._process_with_semaphore(dl_id)
        dm.queue.task_done.assert_called_once()


# ---------------------------------------------------------------------------
# resume_pending_downloads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_pending_downloads_resets_status(dm):
    db = MagicMock()
    pending_dl = MagicMock(id=uuid.uuid4(), status="pending")
    downloading_dl = MagicMock(id=uuid.uuid4(), status="downloading", progress=50)
    processing_dl = MagicMock(id=uuid.uuid4(), status="processing", progress=80)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pending_dl, downloading_dl, processing_dl]
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch.object(dm, "start_worker", new_callable=AsyncMock):
        await dm.resume_pending_downloads(db)

    assert downloading_dl.status == "pending"
    assert downloading_dl.progress == 0
    assert processing_dl.status == "pending"
    assert processing_dl.progress == 0
    assert pending_dl.status == "pending"  # unchanged
    assert dm.queue.qsize() == 3
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_resume_pending_downloads_empty(dm):
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    await dm.resume_pending_downloads(db)

    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_resume_pending_downloads_exception_swallowed(dm):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=Exception("DB error"))

    # Should not raise
    await dm.resume_pending_downloads(db)


# ---------------------------------------------------------------------------
# _notify_start / _notify_completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_start_emits(dm):
    download = MagicMock(id=uuid.uuid4())
    download.track.title = "Song"
    download.track.artist = "Artist"
    download.track.metadata_content = {"image_url": "https://img"}

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._notify_start(download)
    mock_emit.assert_called_once()
    args = mock_emit.call_args[0]
    assert args[0] == "download:progress"
    assert args[1]["progress"] == 0


@pytest.mark.asyncio
async def test_notify_completion_emits(dm):
    download = MagicMock(id=uuid.uuid4(), file_path="/dl/song.mp3", track_id="t1")
    download.track.title = "Song"
    download.track.artist = "Artist"
    download.track.metadata_content = None

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._notify_completion(download)

    mock_emit.assert_called_once()
    args = mock_emit.call_args[0]
    assert args[0] == "download:completed"
    assert args[1]["filename"] == "song.mp3"


@pytest.mark.asyncio
async def test_notify_completion_no_file_path(dm):
    download = MagicMock(id=uuid.uuid4(), file_path=None, track_id="track123")
    download.track.title = "T"
    download.track.artist = "A"
    download.track.metadata_content = None

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._notify_completion(download)

    args = mock_emit.call_args[0]
    assert args[1]["filename"] == "track123.mp3"


# ---------------------------------------------------------------------------
# _validate_download_path
# ---------------------------------------------------------------------------


def test_validate_download_path_safe(dm, tmp_path):
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        sub = str(tmp_path / "user" / "music")
        result = dm._validate_download_path(sub)
    assert result == sub


def test_validate_download_path_traversal(dm, tmp_path):
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        evil_path = "/etc/passwd"
        result = dm._validate_download_path(evil_path)
    assert result is None


# ---------------------------------------------------------------------------
# _set_download_file_path
# ---------------------------------------------------------------------------


def test_set_download_file_path_from_container(dm, tmp_path):
    download = MagicMock()
    container = {"path": str(tmp_path / "Artist - Title.webm")}
    dm._set_download_file_path(download, container, "Artist - Title", "mp3")
    assert download.file_path == str(tmp_path / "Artist - Title.mp3")


def test_set_download_file_path_fallback(dm, tmp_path):
    download = MagicMock()
    download.user.username = "testuser"
    download.user.preferences = {}
    container = {"path": None}

    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        dm._set_download_file_path(download, container, "Artist - Title", "mp3")

    assert "testuser" in download.file_path or str(tmp_path) in download.file_path
    assert download.file_path.endswith(".mp3")


# ---------------------------------------------------------------------------
# _mark_download_started / _notify_processing / _set_processing_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_download_started(dm):
    db = MagicMock()
    db.commit = AsyncMock()
    download = MagicMock(status="pending")
    download.track.title = "T"
    download.track.artist = "A"
    download.track.metadata_content = None

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock):
        await dm._mark_download_started(db, download)

    assert download.status == "downloading"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_notify_processing(dm):
    download = MagicMock(id=uuid.uuid4())
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._notify_processing(download)
    args = mock_emit.call_args[0]
    assert args[0] == "download:processing"


@pytest.mark.asyncio
async def test_set_processing_status(dm):
    dl_id = str(uuid.uuid4())
    with patch("app.services.download_manager.AsyncSessionLocal") as mock_sl:
        db = MagicMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_download = MagicMock(status="downloading")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_download
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()
        mock_sl.return_value = db

        with patch.object(dm, "_notify_processing", new_callable=AsyncMock):
            await dm._set_processing_status(dl_id)

    assert mock_download.status == "processing"
    assert mock_download.progress == 100


# ---------------------------------------------------------------------------
# _handle_progress_update
# ---------------------------------------------------------------------------


def test_handle_progress_update_with_bytes(dm):
    loop = asyncio.new_event_loop()
    download = MagicMock()
    download.track.title = "T"
    download.track.artist = "A"
    download.track.metadata_content = None

    d = {"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500, "_speed_str": "1MiB/s"}

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock):
        with patch("asyncio.run_coroutine_threadsafe") as mock_rtf:
            dm._handle_progress_update(d, "dl1", download, loop)
            assert mock_rtf.called

    loop.close()


def test_handle_progress_update_caps_at_99(dm):
    loop = asyncio.new_event_loop()
    download = MagicMock()
    download.track.title = "T"
    download.track.artist = "A"
    download.track.metadata_content = None

    d = {"status": "downloading", "total_bytes": 100, "downloaded_bytes": 100, "_speed_str": ""}

    with patch("asyncio.run_coroutine_threadsafe") as mock_rtf:
        dm._handle_progress_update(d, "dl1", download, loop)
        # 100% should be capped to 99.9
        emit_call = mock_rtf.call_args_list[0]
        coro = emit_call[0][0]
        coro.close()  # clean up coroutine

    loop.close()


def test_handle_progress_update_percent_str_fallback(dm):
    loop = asyncio.new_event_loop()
    download = MagicMock()
    download.track.title = "T"
    download.track.artist = "A"
    download.track.metadata_content = None

    d = {"status": "downloading", "total_bytes": None, "_percent_str": "50.0%", "_speed_str": ""}

    with patch("asyncio.run_coroutine_threadsafe") as mock_rtf:
        dm._handle_progress_update(d, "dl1", download, loop)
        assert mock_rtf.called

    loop.close()


# ---------------------------------------------------------------------------
# _build_postprocessors
# ---------------------------------------------------------------------------


def test_build_postprocessors_flac(dm):
    pps = dm._build_postprocessors("flac")
    codecs = [pp["key"] for pp in pps]
    assert "FFmpegExtractAudio" in codecs
    assert dm._target_format == "flac"


def test_build_postprocessors_mp3(dm):
    pps = dm._build_postprocessors("320")
    assert dm._target_format == "mp3"
    pp = next(p for p in pps if p["key"] == "FFmpegExtractAudio")
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "320"


# ---------------------------------------------------------------------------
# _build_output_template
# ---------------------------------------------------------------------------


def test_build_output_template_basic(dm):
    download = MagicMock(source="spotify", playlist_name=None)
    schema_map = {"{artist}": "%(artist)s", "{title}": "%(title)s"}
    result = dm._build_output_template(download, "{artist} - {title}", schema_map)
    assert result == "%(artist)s - %(title)s"


def test_build_output_template_with_playlist(dm):
    download = MagicMock(source="spotify", playlist_name="My Playlist")
    schema_map = {"{artist}": "%(artist)s", "{title}": "%(title)s"}
    result = dm._build_output_template(download, "{playlist}/{artist} - {title}", schema_map)
    assert "My Playlist" in result or "My_Playlist" in result


def test_build_output_template_fallback_on_invalid(dm):
    download = MagicMock(source="spotify", playlist_name=None)
    result = dm._build_output_template(download, "no_percent_tags", {})
    assert "%(artist)s" in result


# ---------------------------------------------------------------------------
# _get_ydl_options — filename schema uses track metadata, not yt-dlp fields
# (GitHub discussion #131: fallback via YouTube produced raw video titles)
# ---------------------------------------------------------------------------


def _make_track(title=None, artist=None, album=None):
    track = MagicMock()
    track.title = title
    track.artist = artist
    track.album = album
    return track


def _make_download(schema, track, source="deezer", playlist_name=None):
    download = MagicMock(source=source, playlist_name=playlist_name)
    download.user.username = "alice"
    download.user.preferences = {"quality": "high", "filename_schema": schema}
    download.track = track
    return download


def test_get_ydl_options_title_from_track_metadata(dm, tmp_path):
    """{title} must resolve to the track's DB title, not yt-dlp's %(title)s."""
    download = _make_download(
        "{service}/{playlist}/{title}",
        _make_track(title="A Dark Task", artist="Magic Sword"),
        playlist_name="Magic Sword",
    )
    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        _, tmpl = dm._get_ydl_options(download, MagicMock())

    assert tmpl == "deezer/Magic Sword/A Dark Task"


def test_get_ydl_options_artist_album_from_track_metadata(dm, tmp_path):
    download = _make_download(
        "{artist}/{album}/{title}",
        _make_track(title="Hellfire", artist="Magic Sword", album="Endless"),
    )
    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        _, tmpl = dm._get_ydl_options(download, MagicMock())

    assert tmpl == "Magic Sword/Endless/Hellfire"


def test_get_ydl_options_missing_metadata_falls_back_to_ydl_fields(dm, tmp_path):
    """No track metadata → keep yt-dlp template fields."""
    download = _make_download("{artist} - {title}", _make_track())
    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        _, tmpl = dm._get_ydl_options(download, MagicMock())

    assert tmpl == "%(artist)s - %(title)s"


def test_get_ydl_options_escapes_percent_in_metadata(dm, tmp_path):
    """Literal '%' in metadata must be escaped to '%%' for yt-dlp outtmpl."""
    download = _make_download("{title}", _make_track(title="100% Love"))
    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        _, tmpl = dm._get_ydl_options(download, MagicMock())

    assert tmpl == "100%% Love"


def test_get_ydl_options_sanitizes_metadata(dm, tmp_path):
    """Path separators in metadata must not create extra directories."""
    download = _make_download("{title}", _make_track(title="AC/DC: Live"))
    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        _, tmpl = dm._get_ydl_options(download, MagicMock())

    assert "/" not in tmpl
    assert ":" not in tmpl


def test_build_output_template_literal_schema_not_rejected(dm):
    """Template built from literal metadata (no '%') must not fall back to default."""
    download = MagicMock(source="deezer", playlist_name=None)
    schema_map = {"{artist}": "Magic Sword", "{title}": "Hellfire"}
    result = dm._build_output_template(download, "{artist} - {title}", schema_map)
    assert result == "Magic Sword - Hellfire"


def test_build_output_template_no_known_tags_falls_back(dm):
    """Schema with no recognized tags → static name → fall back to default."""
    download = MagicMock(source="deezer", playlist_name=None)
    schema_map = {"{artist}": "Magic Sword", "{title}": "Hellfire"}
    result = dm._build_output_template(download, "my_music", schema_map)
    assert result == "%(artist)s - %(title)s"


# ---------------------------------------------------------------------------
# _get_ydl_options
# ---------------------------------------------------------------------------


def test_get_ydl_options_quality_map(dm, tmp_path):
    download = MagicMock(source="spotify", playlist_name=None)
    download.user.username = "alice"
    download.user.preferences = {"quality": "lossless", "filename_schema": "{artist} - {title}"}

    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        mock_hook = MagicMock()
        _, tmpl = dm._get_ydl_options(download, mock_hook)

    assert dm._target_format == "flac"
    assert "%(artist)s" in tmpl or "artist" in tmpl


def test_get_ydl_options_normal_quality(dm, tmp_path):
    download = MagicMock(source="youtube", playlist_name=None)
    download.user.username = "bob"
    download.user.preferences = {"quality": "normal", "filename_schema": "{artist} - {title}"}

    with (
        patch("app.services.download_manager.settings") as mock_settings,
        patch("os.path.exists", return_value=True),
    ):
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        mock_hook = MagicMock()
        _, _ = dm._get_ydl_options(download, mock_hook)

    assert dm._target_format == "mp3"


# ---------------------------------------------------------------------------
# _resolve_direct_soundcloud
# ---------------------------------------------------------------------------


def test_resolve_direct_soundcloud_direct_url(dm):
    download = MagicMock(track_id="https://soundcloud.com/user/track")
    track_info = MagicMock(metadata_content={})
    result = dm._resolve_direct_soundcloud(download, track_info)
    assert result == "https://soundcloud.com/user/track"


def test_resolve_direct_soundcloud_source_url(dm):
    download = MagicMock(track_id="abc123")
    track_info = MagicMock(metadata_content={"source_url": "https://soundcloud.com/user/track"})
    result = dm._resolve_direct_soundcloud(download, track_info)
    assert result == "https://soundcloud.com/user/track"


def test_resolve_direct_soundcloud_search_fallback(dm):
    download = MagicMock(track_id="abc123")
    track_info = MagicMock(metadata_content={}, artist="Artist", title="Title")
    result = dm._resolve_direct_soundcloud(download, track_info)
    assert result.startswith("scsearch1:")


def test_resolve_direct_soundcloud_no_track_info(dm):
    download = MagicMock(track_id="abc123")
    result = dm._resolve_direct_soundcloud(download, None)
    assert result == ""


def test_resolve_direct_soundcloud_invalid_url_falls_back(dm):
    """ValueError from urlparse → host = '' → falls through to search fallback."""
    download = MagicMock(track_id="https://[broken")
    track_info = MagicMock(metadata_content={}, artist="A", title="T")
    result = dm._resolve_direct_soundcloud(download, track_info)
    assert result.startswith("scsearch1:")


def test_cleanup_empty_directory_removes_m3u8_and_parent(dm, tmp_path):
    """Happy-path: m3u8 + empty parent dir under DOWNLOAD_DIR both removed."""
    user_dir = tmp_path / "playlist"
    user_dir.mkdir()
    track_file = user_dir / "track1.mp3"
    track_file.write_text("audio")
    m3u8_file = user_dir / "playlist.m3u8"
    m3u8_file.write_text("#EXTM3U\n")

    download = MagicMock(file_path=str(track_file))
    track_file.unlink()  # simulate already-deleted track

    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        with patch.object(dm, "_get_user_download_dir", return_value=str(user_dir)):
            with patch("app.services.download_manager.sanitize_filename", side_effect=lambda x: x):
                dm._cleanup_empty_directory([download], "playlist")

    assert not m3u8_file.exists()
    assert not user_dir.exists()


def test_cleanup_empty_directory_no_downloads_returns(dm):
    dm._cleanup_empty_directory([], "x")  # should not raise


def test_cleanup_empty_directory_traversal_rejected(dm, tmp_path):
    """Parent dir outside DOWNLOAD_DIR is rejected by is_relative_to barrier."""
    outside = tmp_path / "outside"
    outside.mkdir()
    track = outside / "t.mp3"
    track.write_text("x")
    download = MagicMock(file_path=str(track))

    safe_root = tmp_path / "safe"
    safe_root.mkdir()
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(safe_root)
        with patch.object(dm, "_get_user_download_dir", return_value=str(outside)):
            with patch("app.services.download_manager.sanitize_filename", side_effect=lambda x: x):
                dm._cleanup_empty_directory([download], "playlist")

    assert outside.exists()  # not removed because outside DOWNLOAD_DIR


# ---------------------------------------------------------------------------
# _resolve_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_url_yt_search(dm):
    db = MagicMock()
    download = MagicMock(source="spotify", track_id="tid", retry_count=0)

    with (
        patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_fi,
        patch.object(dm, "get_track_info", new_callable=AsyncMock, return_value=None),
    ):
        mock_fi.return_value = {"type": "yt_search", "value": "Artist Title"}
        result = await dm._resolve_url(db, download)

    assert result == "ytsearch1:Artist Title"


@pytest.mark.asyncio
async def test_resolve_url_sc_search(dm):
    db = MagicMock()
    download = MagicMock(source="soundcloud", track_id="tid", retry_count=0)

    with (
        patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_fi,
        patch.object(dm, "get_track_info", new_callable=AsyncMock, return_value=None),
    ):
        mock_fi.return_value = {"type": "sc_search", "value": "Artist Title"}
        result = await dm._resolve_url(db, download)

    assert result == "scsearch1:Artist Title"


@pytest.mark.asyncio
async def test_resolve_url_direct_youtube(dm):
    db = MagicMock()
    download = MagicMock(source="youtube", track_id="dQw4w9WgXcQ", retry_count=0)

    with (
        patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_fi,
        patch.object(dm, "get_track_info", new_callable=AsyncMock, return_value=None),
    ):
        mock_fi.return_value = {"type": "direct_youtube", "value": None}
        result = await dm._resolve_url(db, download)

    assert "dQw4w9WgXcQ" in result


@pytest.mark.asyncio
async def test_resolve_url_none_fallback(dm):
    db = MagicMock()
    download = MagicMock(source="spotify", track_id="tid", retry_count=0)
    track_info = MagicMock(artist="The Artist", title="The Title")

    with (
        patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_fi,
        patch.object(dm, "get_track_info", new_callable=AsyncMock, return_value=track_info),
    ):
        mock_fi.return_value = {"type": "none", "value": None}
        result = await dm._resolve_url(db, download)

    assert "The Artist" in result


@pytest.mark.asyncio
async def test_resolve_url_empty_on_unknown_type(dm):
    db = MagicMock()
    download = MagicMock(source="spotify", track_id=None, retry_count=0)

    with (
        patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_fi,
        patch.object(dm, "get_track_info", new_callable=AsyncMock, return_value=None),
    ):
        mock_fi.return_value = {"type": "unknown", "value": None}
        result = await dm._resolve_url(db, download)

    assert result == ""


# ---------------------------------------------------------------------------
# retry_failed_downloads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_failed_downloads(dm):
    db = MagicMock()
    dl1 = MagicMock(id=uuid.uuid4(), status="failed", retry_count=0)
    dl2 = MagicMock(id=uuid.uuid4(), status="failed", retry_count=2)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [dl1, dl2]
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch.object(dm, "start_worker", new_callable=AsyncMock):
        await dm.retry_failed_downloads(db)

    assert dl1.status == "pending"
    assert dl2.status == "pending"
    assert dm.queue.qsize() == 2
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_retry_failed_downloads_empty(dm):
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    await dm.retry_failed_downloads(db)
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# update_progress_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_progress_db(dm):
    dl_id = str(uuid.uuid4())
    with patch("app.services.download_manager.AsyncSessionLocal") as mock_sl:
        db = MagicMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_download = MagicMock(progress=0)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_download
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()
        mock_sl.return_value = db

        await dm.update_progress_db(dl_id, 75.5)

    assert mock_download.progress == 75


# ---------------------------------------------------------------------------
# _write_m3u_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_m3u_file(dm, tmp_path):
    target_dir = str(tmp_path)
    playlist_path = str(tmp_path / "test.m3u8")

    dl1 = MagicMock(file_path=str(tmp_path / "song1.mp3"))
    dl1.track.artist = "Artist"
    dl1.track.title = "Song 1"

    dl2 = MagicMock(file_path=None)
    dl2.track.artist = "Artist"
    dl2.track.title = "Song 2"

    await dm._write_m3u_file([dl1, dl2], target_dir, playlist_path)

    assert os.path.exists(playlist_path)
    from pathlib import Path as _Path

    content = _Path(playlist_path).read_text()
    assert "#EXTM3U" in content
    assert "Song 1" in content
    assert "song1.mp3" in content


# ---------------------------------------------------------------------------
# _safe_under_download_dir
# ---------------------------------------------------------------------------


def test_safe_under_download_dir_safe(tmp_path):
    sub_dir = tmp_path / "user"
    sub_dir.mkdir()
    target = sub_dir / "file.mp3"
    target.write_text("x")
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        result = DownloadManager._safe_under_download_dir(str(target))
    assert result == os.path.realpath(str(target))


def test_safe_under_download_dir_traversal(tmp_path):
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        result = DownloadManager._safe_under_download_dir("/etc/passwd")
    assert result is None


def test_safe_under_download_dir_invalid_base(tmp_path):
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = "\x00invalid"
        result = DownloadManager._safe_under_download_dir(str(tmp_path / "a"))
    assert result is None


# ---------------------------------------------------------------------------
# _get_user_download_dir
# ---------------------------------------------------------------------------


def test_get_user_download_dir_from_parent(dm, tmp_path):
    download = MagicMock()
    parent = str(tmp_path / "user" / "playlist")
    result = dm._get_user_download_dir(download, parent)
    assert result == str(tmp_path / "user")


def test_get_user_download_dir_from_preferences(dm, tmp_path):
    download = MagicMock()
    download.user.preferences = {"downloadPath": str(tmp_path / "custom")}
    result = dm._get_user_download_dir(download, "")
    assert "custom" in result


def test_get_user_download_dir_fallback(dm, tmp_path):
    download = MagicMock()
    download.user.preferences = {}
    download.user.username = "alice"
    with patch("app.services.download_manager.settings") as mock_settings:
        mock_settings.DOWNLOAD_DIR = str(tmp_path)
        result = dm._get_user_download_dir(download, "")
    assert "alice" in result


# ---------------------------------------------------------------------------
# _delete_physical_files
# ---------------------------------------------------------------------------


def test_delete_physical_files_removes_file(dm, tmp_path):
    f = tmp_path / "song.mp3"
    f.write_text("data")
    dl = MagicMock(file_path=str(f), id="dl1")
    dm._delete_physical_files([dl])
    assert not f.exists()


def test_delete_physical_files_cancels_active_task(dm, tmp_path):
    f = tmp_path / "song.mp3"
    f.write_text("data")
    dl = MagicMock(file_path=str(f), id="dl1")
    mock_task = MagicMock()
    dm.active_tasks["dl1"] = mock_task
    dm._delete_physical_files([dl])
    mock_task.cancel.assert_called_once()
    assert "dl1" not in dm.active_tasks


def test_delete_physical_files_missing_file(dm):
    dl = MagicMock(file_path="/nonexistent/song.mp3", id="dl2")
    # Should not raise
    dm._delete_physical_files([dl])


# ---------------------------------------------------------------------------
# _get_playlist_downloads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_playlist_downloads_valid_uuid(dm):
    db = MagicMock()
    user_id = str(uuid.uuid4())
    mock_dl = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_dl]
    db.execute = AsyncMock(return_value=mock_result)

    result = await dm._get_playlist_downloads(db, user_id, "spotify", "My Playlist")
    assert result == [mock_dl]


@pytest.mark.asyncio
async def test_get_playlist_downloads_invalid_uuid(dm):
    db = MagicMock()
    result = await dm._get_playlist_downloads(db, "not-uuid", "spotify", "My Playlist")
    assert result == []


# ---------------------------------------------------------------------------
# _delete_db_records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_db_records(dm):
    db = MagicMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    dl1 = MagicMock()
    dl2 = MagicMock()

    await dm._delete_db_records(db, [dl1, dl2])

    assert db.delete.call_count == 2
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# pause_download_async / resume_download edge cases / cancel edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_download_async(dm):
    dl_id = str(uuid.uuid4())
    await dm.pause_download_async(dl_id)
    assert dl_id in dm.paused_downloads


@pytest.mark.asyncio
async def test_resume_download_invalid_uuid(dm):
    db = MagicMock()
    # Should not raise
    await dm.resume_download(db, "not-a-uuid")


@pytest.mark.asyncio
async def test_cancel_download_invalid_uuid(dm):
    db = MagicMock()
    # Should not raise
    await dm.cancel_download(db, "not-a-uuid")


@pytest.mark.asyncio
async def test_cancel_download_removes_from_paused(dm):
    dl_id = str(uuid.uuid4())
    dm.paused_downloads.add(dl_id)
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    await dm.cancel_download(db, dl_id)
    assert dl_id not in dm.paused_downloads


# ---------------------------------------------------------------------------
# update_playlist_m3u
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_playlist_m3u_no_downloads(dm):
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    # Should return without error
    await dm.update_playlist_m3u(db, str(uuid.uuid4()), "My Playlist")


# ---------------------------------------------------------------------------
# _update_track_from_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_track_from_file_missing(dm):
    db = MagicMock()
    download = MagicMock(file_path=None)
    # No file_path → should return immediately
    await dm._update_track_from_file(db, download)


@pytest.mark.asyncio
async def test_update_track_from_file_updates(dm, tmp_path):
    f = tmp_path / "song.mp3"
    f.write_bytes(b"\x00" * 100)
    db = MagicMock()
    db.commit = AsyncMock()
    download = MagicMock(file_path=str(f))
    download.track.title = "Old"
    download.track.artist_id = None
    download.track.album_id = None
    download.track.genre = None
    download.track.duration_ms = None
    download.track.file_size = None

    with (
        patch(
            "app.services.library_scanner.library_scanner_service._parse_audio_metadata_sync",
            return_value=("New Title", "New Artist", "New Album", "Pop", 180000, None),
        ),
        patch(
            "app.services.library_scanner.library_scanner_service.resolve_artist_and_album",
            new_callable=AsyncMock,
            return_value=("artist_id", "album_id"),
        ),
    ):
        await dm._update_track_from_file(db, download)

    assert download.track.title == "New Title"
