"""Extended unit tests for library_scanner helper methods targeting missing coverage."""

import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.services.library_scanner import UNKNOWN_ALBUM, UNKNOWN_ARTIST, LibraryScannerService


@pytest.fixture
def scanner():
    return LibraryScannerService()


# ─── _validate_scan_path ───────────────────────────────────────────────────────


def test_validate_scan_path_cross_platform_error(scanner):
    """ValueError from commonpath on different drives (Windows path error)."""
    scanner.base_dir = os.path.abspath("/music")
    with patch("os.path.commonpath", side_effect=ValueError("Different drives")):
        with pytest.raises(ValueError, match="Access denied"):
            scanner._validate_scan_path(os.path.abspath("/music/subdir"))


# ─── _get_known_paths ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_known_paths_invalid_uuid(scanner, db_session):
    result = await scanner._get_known_paths(db_session, "not-a-valid-uuid")
    assert result == set()


# ─── _update_meta_from_tags ───────────────────────────────────────────────────


def test_update_meta_from_tags_updates_artist(scanner):
    m = {"TPE1": MagicMock(__str__=lambda s: "Real Artist"), "TIT2": MagicMock(__str__=lambda s: "Real Title")}
    result = scanner._update_meta_from_tags(
        m, (os.path.splitext("song.mp3")[0], UNKNOWN_ARTIST, UNKNOWN_ALBUM, None), "song.mp3"
    )
    assert result[1] == "Real Artist"


def test_update_meta_from_tags_updates_title(scanner):
    m = {"TIT2": MagicMock(__str__=lambda s: "Real Title")}
    result = scanner._update_meta_from_tags(m, ("song", UNKNOWN_ARTIST, UNKNOWN_ALBUM, None), "song.mp3")
    assert result[0] == "Real Title"


def test_update_meta_from_tags_updates_album(scanner):
    m = {"TALB": MagicMock(__str__=lambda s: "Real Album")}
    result = scanner._update_meta_from_tags(m, ("title", "artist", UNKNOWN_ALBUM, None), "song.mp3")
    assert result[2] == "Real Album"


def test_update_meta_from_tags_updates_genre(scanner):
    m = {"TCON": MagicMock(__str__=lambda s: "Rock")}
    result = scanner._update_meta_from_tags(m, ("title", "artist", "album", None), "song.mp3")
    assert result[3] == "Rock"


def test_update_meta_from_tags_no_update_when_values_set(scanner):
    m = {"TPE1": MagicMock(), "TIT2": MagicMock(), "TALB": MagicMock()}
    result = scanner._update_meta_from_tags(m, ("My Title", "My Artist", "My Album", "Jazz"), "song.mp3")
    assert result[0] == "My Title"
    assert result[1] == "My Artist"
    assert result[2] == "My Album"


# ─── _extract_lyrics_from_lrc_file ────────────────────────────────────────────


def test_extract_lyrics_from_lrc_file_exists(scanner):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    lrc_path = os.path.splitext(tmp_path)[0] + ".lrc"
    try:
        with open(lrc_path, "w") as f:
            f.write("[00:01.00] Line one\n[00:02.00] Line two\n")
        result = scanner._extract_lyrics_from_lrc_file(tmp_path)
        assert result is not None
        assert "Line one" in result
    finally:
        os.unlink(tmp_path)
        if os.path.exists(lrc_path):
            os.unlink(lrc_path)


def test_extract_lyrics_from_lrc_file_empty(scanner):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    lrc_path = os.path.splitext(tmp_path)[0] + ".lrc"
    try:
        with open(lrc_path, "w") as f:
            f.write("   ")  # Only whitespace
        result = scanner._extract_lyrics_from_lrc_file(tmp_path)
        assert result is None
    finally:
        os.unlink(tmp_path)
        if os.path.exists(lrc_path):
            os.unlink(lrc_path)


def test_extract_lyrics_from_lrc_file_not_exists(scanner):
    result = scanner._extract_lyrics_from_lrc_file("/nonexistent/path/song.mp3")
    assert result is None


# ─── _extract_lyrics_from_tags ────────────────────────────────────────────────


def test_extract_lyrics_no_tags_attr(scanner):
    m = MagicMock(spec=[])  # no 'tags' attribute
    result = scanner._extract_lyrics_from_tags(m)
    assert result is None


def test_extract_lyrics_uslt_eng(scanner):
    m = MagicMock()
    m.tags = {"USLT::eng": MagicMock(__str__=lambda s: "English lyrics")}
    result = scanner._extract_lyrics_from_tags(m)
    assert result == "English lyrics"


def test_extract_lyrics_uslt_plain(scanner):
    m = MagicMock()
    m.tags = {"USLT:": MagicMock(__str__=lambda s: "Plain lyrics")}
    result = scanner._extract_lyrics_from_tags(m)
    assert result == "Plain lyrics"


def test_extract_lyrics_uslt_generic_frame(scanner):
    class FakeTags:
        def __contains__(self, key):
            return False  # not "USLT::eng" or "USLT:"

        def __iter__(self):
            return iter(["USLT:XXX"])

        def __getitem__(self, key):
            return "Generic frame lyrics"

    m = MagicMock()
    m.tags = FakeTags()
    result = scanner._extract_lyrics_from_tags(m)
    assert result == "Generic frame lyrics"


def test_extract_lyrics_flac_vorbis(scanner):
    m = MagicMock()
    tags_mock = MagicMock()
    tags_mock.__contains__ = MagicMock(side_effect=lambda key: key == "lyrics")
    tags_mock.__iter__ = MagicMock(return_value=iter(["lyrics"]))
    tags_mock.__getitem__ = MagicMock(return_value=["FLAC lyrics line"])
    m.tags = tags_mock
    result = scanner._extract_lyrics_from_tags(m)
    assert result == "FLAC lyrics line"


# ─── _infer_source_info ───────────────────────────────────────────────────────


def test_infer_source_info_deep_path(scanner):
    source, playlist = scanner._infer_source_info("/music/spotify/My Playlist/song.mp3", "/music")
    assert source == "spotify"
    assert playlist == "My Playlist"


def test_infer_source_info_two_parts_known_source(scanner):
    source, playlist = scanner._infer_source_info("/music/youtube/song.mp3", "/music")
    assert source == "youtube"
    assert playlist == "Uncategorized"


def test_infer_source_info_two_parts_unknown(scanner):
    source, playlist = scanner._infer_source_info("/music/misc/song.mp3", "/music")
    assert source == "local_import"
    assert playlist == "misc"


def test_infer_source_info_single_file(scanner):
    source, playlist = scanner._infer_source_info("/music/song.mp3", "/music")
    assert source == "local_import"
    assert playlist == "Imported"


# ─── _import_playlist ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_playlist_basic(scanner, db_session, admin_user):
    with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False) as f:
        f.write("# M3U playlist\n")
        f.write("/nonexistent/track.mp3\n")
        playlist_path = f.name

    try:
        # Should not raise even if tracks not found
        await scanner._import_playlist(db_session, playlist_path, str(admin_user.id))
    finally:
        os.unlink(playlist_path)


@pytest.mark.asyncio
async def test_import_playlist_creates_playlist_with_tracks(scanner, db_session, admin_user):
    from app.models.download import Download
    from app.models.track import Track

    track = Track(id=uuid.uuid4(), title="Test Track", artist="Artist")
    db_session.add(track)

    dl = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        file_path="/music/test_track.mp3",
    )
    db_session.add(dl)
    await db_session.commit()

    with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, dir=os.path.dirname("/tmp/")) as f:
        f.write("/music/test_track.mp3\n")
        playlist_path = f.name

    try:
        await scanner._import_playlist(db_session, playlist_path, str(admin_user.id))
    finally:
        os.unlink(playlist_path)
