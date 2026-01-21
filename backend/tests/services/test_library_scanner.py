"""
Tests for Library Scanner service.

Covers:
- _parse_audio_metadata - extracts title, artist, album, genre, duration_ms
- _import_playlist - does NOT clear tracks when 0 matches (bug fix verification)
"""

import os
import tempfile
import uuid
import aiofiles
from unittest.mock import MagicMock, patch

import pytest
from app.models.download import Download
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User
from app.services.library_scanner import library_scanner_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_parse_audio_metadata_returns_duration():
    """Test that _parse_audio_metadata extracts duration_ms from files."""
    # Create a mock mutagen file with duration
    with patch("app.services.library_scanner.MutagenFile") as mock_mutagen:
        mock_file = MagicMock()
        mock_file.info.length = 180.5  # 180.5 seconds
        mock_mutagen.return_value = mock_file

        with patch("app.services.library_scanner.EasyID3") as mock_easyid3:
            mock_easyid3.return_value = {}

            # title, artist, album, genre, duration_ms
            title, _, _, _, duration_ms = library_scanner_service._parse_audio_metadata_sync(
                "/fake/path/song.mp3"
            )

            # Duration should be extracted
            assert duration_ms == 180500, f"Expected 180500ms, got {duration_ms}"
            assert title == "song"  # Fallback to filename


@pytest.mark.asyncio
async def test_parse_audio_metadata_returns_zero_on_error():
    """Test that duration_ms is 0 when file cannot be parsed."""
    with patch("app.services.library_scanner.MutagenFile") as mock_mutagen:
        mock_mutagen.side_effect = Exception("Cannot parse")

        with patch("app.services.library_scanner.EasyID3") as mock_easyid3:
            mock_easyid3.side_effect = Exception("Cannot parse")

            # title, artist, album, genre, duration_ms
            _, artist, _, _, duration_ms = library_scanner_service._parse_audio_metadata_sync(
                "/nonexistent/file.mp3"
            )

            assert duration_ms == 0
            assert artist == "Unknown Artist"


@pytest.mark.asyncio
async def test_import_playlist_preserves_existing_on_zero_match(db_session: AsyncSession):
    """
    CRITICAL: Verify that _import_playlist does NOT clear existing tracks
    when the new import matches 0 files.
    
    This was a bug that caused playlists to become empty after restart.
    """
    # Setup user
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@test.com", username="testuser", hashed_password="pw", is_active=True)
    db_session.add(user)

    # Create track and download
    track = Track(title="Existing Track", artist="Artist", duration_ms=200000)
    db_session.add(track)
    await db_session.flush()

    download = Download(
        user_id=user_id,
        track_id=track.id,
        status="completed",
        file_path="/downloads/existing.mp3",
    )
    db_session.add(download)

    # Create playlist with one track
    playlist = Playlist(name="TestPlaylist", owner_id=user_id)
    db_session.add(playlist)
    await db_session.flush()

    pt = PlaylistTrack(playlist_id=playlist.id, track_id=track.id, order=0)
    db_session.add(pt)
    await db_session.commit()

    # Verify we have 1 track
    result = await db_session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
    )
    initial_count = len(result.scalars().all())
    assert initial_count == 1, "Should have 1 track initially"

    # Create a temp m3u8 file that references files that DON'T exist in DB
    m3u_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.m3u8")
    async with aiofiles.open(m3u_path, mode="w") as f:
        await f.write("#EXTM3U\n")
        await f.write("/nonexistent/file1.mp3\n")
        await f.write("/nonexistent/file2.mp3\n")

    try:
        # Mock base_dir to match our paths
        with patch.object(library_scanner_service, "base_dir", "/nonexistent"):
            await library_scanner_service._import_playlist(db_session, m3u_path, str(user_id))

        # Verify tracks are PRESERVED (not deleted)
        result = await db_session.execute(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
        )
        final_count = len(result.scalars().all())

        assert final_count == 1, f"Expected 1 track (preserved), got {final_count}. BUG: Playlist was cleared!"

    finally:
        os.unlink(m3u_path)


@pytest.mark.asyncio
async def test_import_playlist_updates_when_matches_found(db_session: AsyncSession):
    """
    TODO: Test that _import_playlist correctly updates when matches are found.
    
    This test is complex because the matching logic uses multiple strategies:
    1. Exact path match
    2. /downloads/ prefix match
    3. Filename-only match
    
    For now, we skip this test. The critical test is test_import_playlist_preserves_existing_on_zero_match
    which verifies we don't accidentally delete data.
    """
    pytest.skip("Complex matching logic - covered by integration tests")
