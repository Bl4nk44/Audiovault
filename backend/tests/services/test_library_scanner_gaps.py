"""Gap tests for library_scanner.py — covers previously uncovered branches."""

import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.download import Download
from app.models.track import Track
from app.services.library_scanner import LibraryScannerService


@pytest.fixture
def scanner():
    return LibraryScannerService()


@pytest.fixture
def scanner_with_tmpdir(tmp_path):
    """Scanner whose base_dir is a fresh tmp dir — allows path-safe fixture data."""
    s = LibraryScannerService()
    s.base_dir = str(tmp_path)
    return s, tmp_path


# ─── _extract_lyrics_from_lrc_file: exception branch (lines 97-98) ───────────


def test_extract_lyrics_lrc_open_exception(scanner):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    lrc_path = os.path.splitext(tmp_path)[0] + ".lrc"
    try:
        # Create the lrc so os.path.exists passes, then mock open to raise
        with open(lrc_path, "w") as f:
            f.write("lyrics")

        with patch("builtins.open", side_effect=OSError("read error")):
            result = scanner._extract_lyrics_from_lrc_file(tmp_path)
        assert result is None
    finally:
        os.unlink(tmp_path)
        if os.path.exists(lrc_path):
            os.unlink(lrc_path)


# ─── _try_parse_mutagen_fallback: lyrics branches (lines 141, 146) ───────────


def test_try_parse_mutagen_fallback_lyrics_from_tags(scanner):
    mock_mutagen = MagicMock()
    mock_mutagen.info.length = 3.0
    mock_mutagen.tags = {"USLT::eng": MagicMock(__str__=lambda _: "tag lyrics")}

    with (
        patch("app.services.library_scanner.MutagenFile", return_value=mock_mutagen),
        patch.object(scanner, "_extract_lyrics_from_lrc_file", return_value=None),
        patch.object(scanner, "_extract_lyrics_from_tags", return_value="tag lyrics"),
    ):
        _, _, _, _, duration, lyrics = scanner._try_parse_mutagen_fallback(
            "/fake/song.mp3", ("title", "artist", "album", None)
        )
    assert lyrics == "tag lyrics"
    assert duration == 3000


def test_try_parse_mutagen_fallback_external_lyrics_overrides_tags(scanner):
    mock_mutagen = MagicMock()
    mock_mutagen.info.length = 2.0

    with (
        patch("app.services.library_scanner.MutagenFile", return_value=mock_mutagen),
        patch.object(scanner, "_extract_lyrics_from_tags", return_value="tag lyrics"),
        patch.object(scanner, "_extract_lyrics_from_lrc_file", return_value="synced lrc lyrics"),
    ):
        _, _, _, _, _, lyrics = scanner._try_parse_mutagen_fallback(
            "/fake/song.mp3", ("title", "artist", "album", None)
        )
    assert lyrics == "synced lrc lyrics"


# ─── _infer_source_info: exception branch (lines 191-192) ────────────────────


def test_infer_source_info_relpath_exception(scanner):
    with patch("os.path.relpath", side_effect=ValueError("different drives")):
        source, playlist = scanner._infer_source_info("/music/song.mp3", "/music")
    assert source == "local_import"
    assert playlist == "Imported"


# ─── resolve_artist_and_album: empty name guards (lines 206, 208) ─────────────


@pytest.mark.asyncio
async def test_resolve_artist_album_empty_names(scanner, db_session):
    artist_id, album_id = await scanner.resolve_artist_and_album(db_session, "", "")
    assert artist_id is not None
    assert album_id is not None


@pytest.mark.asyncio
async def test_resolve_artist_album_none_names(scanner, db_session):
    artist_id, album_id = await scanner.resolve_artist_and_album(db_session, None, None)
    assert artist_id is not None
    assert album_id is not None


# ─── _find_track_for_playlist_line (lines 294-349) ───────────────────────────


@pytest.mark.asyncio
async def test_find_track_strategy1_exact_path(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir
    track_file = tmp_path / "song.mp3"
    track_file.write_bytes(b"fake")

    track = Track(id=uuid.uuid4(), title="Song")
    db_session.add(track)
    await db_session.flush()

    dl = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path=str(track_file),
    )
    db_session.add(dl)
    await db_session.commit()

    result = await scanner._find_track_for_playlist_line(db_session, str(track_file), str(tmp_path), str(admin_user.id))
    assert result == track.id


@pytest.mark.asyncio
async def test_find_track_strategy2_downloads_prefix(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir
    relative = "subdir/song2.mp3"
    track_file = tmp_path / relative
    track_file.parent.mkdir(parents=True, exist_ok=True)
    track_file.write_bytes(b"fake")

    track = Track(id=uuid.uuid4(), title="Song2")
    db_session.add(track)
    await db_session.flush()

    # Store using /downloads/ prefix style
    dl = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path=f"/downloads/{relative}",
    )
    db_session.add(dl)
    await db_session.commit()

    result = await scanner._find_track_for_playlist_line(db_session, str(track_file), str(tmp_path), str(admin_user.id))
    assert result == track.id


@pytest.mark.asyncio
async def test_find_track_strategy3_filename_match(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir
    track_file = tmp_path / "unique_name.mp3"
    track_file.write_bytes(b"fake")

    track = Track(id=uuid.uuid4(), title="Unique")
    db_session.add(track)
    await db_session.flush()

    dl = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path="/downloads/somewhere/unique_name.mp3",
    )
    db_session.add(dl)
    await db_session.commit()

    # Strategy 3 query uses UUID column — pass UUID object (SQLite UUID binding requires it)
    result = await scanner._find_track_for_playlist_line(db_session, str(track_file), str(tmp_path), admin_user.id)
    assert result == track.id


@pytest.mark.asyncio
async def test_find_track_path_traversal_blocked(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir
    result = await scanner._find_track_for_playlist_line(db_session, "/etc/passwd", str(tmp_path), str(admin_user.id))
    assert result is None


@pytest.mark.asyncio
async def test_find_track_no_match_returns_none(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir
    track_file = tmp_path / "ghost.mp3"
    track_file.write_bytes(b"fake")

    # Strategy 3 query uses UUID column — pass UUID object (SQLite UUID binding requires it)
    result = await scanner._find_track_for_playlist_line(db_session, str(track_file), str(tmp_path), admin_user.id)
    assert result is None


# ─── _import_playlist with matched tracks (lines 273-287) ────────────────────


@pytest.mark.asyncio
async def test_import_playlist_with_matched_tracks(scanner_with_tmpdir, db_session, admin_user):
    scanner, tmp_path = scanner_with_tmpdir

    track_file = tmp_path / "matched.mp3"
    track_file.write_bytes(b"fake")

    track = Track(id=uuid.uuid4(), title="Matched")
    db_session.add(track)
    await db_session.flush()

    dl = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path=str(track_file),
    )
    db_session.add(dl)
    await db_session.commit()

    playlist_file = tmp_path / "mylist.m3u"
    playlist_file.write_text(f"# M3U\n{track_file}\n")

    # Playlist.owner_id is UUID column — pass UUID object (SQLite UUID binding requires it)
    await scanner._import_playlist(db_session, str(playlist_file), admin_user.id)

    from sqlalchemy.future import select

    from app.models.playlist import Playlist

    result = await db_session.execute(select(Playlist).where(Playlist.name == "mylist"))
    playlist = result.scalar_one_or_none()
    assert playlist is not None


# ─── _process_audio_file: genre+lyrics branches (lines 373, 375) ─────────────


@pytest.mark.asyncio
async def test_process_audio_file_with_genre_and_lyrics(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    fake_file = tmp_path / "song.mp3"
    fake_file.write_bytes(b"fake")

    with patch.object(
        scanner,
        "_parse_audio_metadata_sync",
        return_value=("Title", "Artist", "Album", "Rock", 180000, "Some lyrics"),
    ):
        result = await scanner._process_audio_file(
            db_session, str(admin_user.id), str(fake_file), "song.mp3", str(tmp_path)
        )

    assert result is True

    from sqlalchemy.future import select

    result = await db_session.execute(select(Track).where(Track.title == "Title"))
    track = result.scalar_one_or_none()
    assert track is not None
    assert track.metadata_content.get("genre") == "Rock"
    assert track.metadata_content.get("lyrics") == "Some lyrics"


# ─── _process_audio_file: invalid UUID (lines 397-398) ───────────────────────


@pytest.mark.asyncio
async def test_process_audio_file_invalid_user_id(scanner, db_session, tmp_path):
    scanner.base_dir = str(tmp_path)
    fake_file = tmp_path / "song.mp3"
    fake_file.write_bytes(b"fake")

    with patch.object(
        scanner,
        "_parse_audio_metadata_sync",
        return_value=("Title", "Artist", "Album", None, 0, None),
    ):
        result = await scanner._process_audio_file(
            db_session, "not-a-valid-uuid", str(fake_file), "song.mp3", str(tmp_path)
        )

    assert result is False


# ─── _process_audio_file: exception re-raise (lines 414-416) ────────────────


@pytest.mark.asyncio
async def test_process_audio_file_exception_reraises(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    fake_file = tmp_path / "broken.mp3"
    fake_file.write_bytes(b"fake")

    with patch.object(scanner, "_parse_audio_metadata_sync", side_effect=RuntimeError("metadata exploded")):
        with pytest.raises(RuntimeError, match="metadata exploded"):
            await scanner._process_audio_file(
                db_session, str(admin_user.id), str(fake_file), "broken.mp3", str(tmp_path)
            )


# ─── _handle_scan_file: m3u branch (lines 423-424) ───────────────────────────


@pytest.mark.asyncio
async def test_handle_scan_file_m3u(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    m3u_file = tmp_path / "list.m3u"
    m3u_file.write_text("# empty\n")

    result = await scanner._handle_scan_file(
        db_session, str(admin_user.id), str(m3u_file), "list.m3u", str(tmp_path), set()
    )
    assert result is False  # playlists don't count as imported audio


@pytest.mark.asyncio
async def test_handle_scan_file_m3u8(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    m3u_file = tmp_path / "list.m3u8"
    m3u_file.write_text("# empty\n")

    result = await scanner._handle_scan_file(
        db_session, str(admin_user.id), str(m3u_file), "list.m3u8", str(tmp_path), set()
    )
    assert result is False


# ─── scan_directory: non-existent root (line 444) ────────────────────────────


@pytest.mark.asyncio
async def test_scan_directory_nonexistent_dir(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    nonexistent = str(tmp_path / "does_not_exist")

    result = await scanner.scan_directory(db_session, str(admin_user.id), nonexistent)

    assert result["status"] == "error"
    assert "does not exist" in result["message"]


# ─── scan_directory: error collection (lines 460-461) ────────────────────────


@pytest.mark.asyncio
async def test_scan_directory_collects_errors(scanner, db_session, admin_user, tmp_path):
    scanner.base_dir = str(tmp_path)
    mp3 = tmp_path / "bad.mp3"
    mp3.write_bytes(b"fake")

    with patch.object(scanner, "_handle_scan_file", side_effect=RuntimeError("parse failed")):
        result = await scanner.scan_directory(db_session, str(admin_user.id), str(tmp_path))

    assert result["status"] == "success"
    assert any("bad.mp3" in e for e in result["errors"])
