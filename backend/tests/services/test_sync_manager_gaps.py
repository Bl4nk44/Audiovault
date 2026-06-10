"""Tests covering remaining uncovered lines in sync_manager.py."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.track import Track
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.services.sync_manager import SyncManager


@pytest.fixture
def manager():
    return SyncManager()


# ─── line 45-47: massive deletion (>20 removals, ratio <=10%) ─────────────────


@pytest.mark.asyncio
async def test_compute_safety_warning_massive_deletion(manager):
    # 300 local, 21 removed => 7% ratio (<=10%), but >20 → massive deletion path
    warning, msg = manager._compute_safety_warning(remove_count=21, local_count=300, remote_ids={"x"})
    assert warning is True
    assert "Massive deletion" in msg


# ─── line 61: watchlist not found ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_watchlist_not_found(manager, db_session):
    with pytest.raises(ValueError, match="Watchlist not found"):
        await manager.analyze_watchlist(db_session, uuid.uuid4(), uuid.uuid4())


# ─── line 83: WatchlistItem with track=None ───────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_watchlist_none_track(manager, db_session):
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="NoneTrack",
        source_id="s1",
    )
    db_session.add(wl)
    await db_session.flush()

    # WatchlistItem without a track (track_id points to nonexistent track)
    wi = WatchlistItem(watchlist_id=wl.id, track_id=uuid.uuid4())
    db_session.add(wi)
    await db_session.commit()

    with patch.object(manager, "_fetch_remote_tracks", new_callable=AsyncMock) as m:
        m.return_value = [{"id": "x", "title": "T", "artist": "A"}]
        report = await manager.analyze_watchlist(db_session, user_id, wl.id)
    # WatchlistItem with null track is skipped; to_remove_count == 0
    assert report["to_remove_count"] == 0


# ─── line 124: _remove_download_if_unreferenced when ref_count > 0 ────────────


@pytest.mark.asyncio
async def test_remove_download_ref_count_nonzero(manager, db_session):
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()

    # Create two watchlists referencing the same track
    wl1 = Watchlist(
        id=uuid.uuid4(), user_id=user_id, watch_type="playlist", source="spotify", source_name="W1", source_id="w1"
    )
    wl2 = Watchlist(
        id=uuid.uuid4(), user_id=user_id, watch_type="playlist", source="spotify", source_name="W2", source_id="w2"
    )
    db_session.add(wl1)
    db_session.add(wl2)
    await db_session.flush()

    track = Track(id=track_id, title="Shared", artist="Art")
    db_session.add(track)
    await db_session.flush()

    wi1 = WatchlistItem(watchlist_id=wl1.id, track_id=track_id)
    wi2 = WatchlistItem(watchlist_id=wl2.id, track_id=track_id)
    db_session.add(wi1)
    db_session.add(wi2)
    await db_session.commit()

    # Still has ref → should return 0 (not delete)
    result = await manager._remove_download_if_unreferenced(db_session, user_id, track_id)
    assert result == 0


# ─── line 128: _remove_download_if_unreferenced when no download exists ───────


@pytest.mark.asyncio
async def test_remove_download_no_download(manager, db_session):
    # No WatchlistItem refs, no Download → return 0
    result = await manager._remove_download_if_unreferenced(db_session, uuid.uuid4(), uuid.uuid4())
    assert result == 0


# ─── line 148: execute_sync with invalid token ────────────────────────────────


@pytest.mark.asyncio
async def test_execute_sync_invalid_token(manager, db_session):
    with pytest.raises(ValueError, match="Invalid or expired sync token"):
        await manager.execute_sync(db_session, uuid.uuid4(), "no-such-token", [])


# ─── lines 200, 203, 206: _fetch_playlist_tracks edge cases ──────────────────


@pytest.mark.asyncio
async def test_fetch_playlist_tracks_no_source(manager):
    wl = Watchlist(watch_type="playlist", source=None, source_id="x")
    result = await manager._fetch_playlist_tracks(wl)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_playlist_tracks_no_provider(manager):
    wl = Watchlist(watch_type="playlist", source="spotify", source_id="x")
    with patch("app.services.sync_manager.provider_manager.get_provider_by_name", return_value=None):
        result = await manager._fetch_playlist_tracks(wl)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_playlist_tracks_empty_metadata(manager):
    wl = Watchlist(watch_type="playlist", source="spotify", source_id="x")
    mock_provider = AsyncMock()
    mock_provider.extract_playlist = AsyncMock(return_value=None)
    with patch("app.services.sync_manager.provider_manager.get_provider_by_name", return_value=mock_provider):
        result = await manager._fetch_playlist_tracks(wl)
    assert result == []


# ─── lines 217-219: _fetch_artist_tracks YouTube path ────────────────────────


@pytest.mark.asyncio
async def test_fetch_artist_tracks_youtube(manager):
    wl = Watchlist(watch_type="artist", source="youtube", source_id="UC123")
    mock_tracks = [{"id": "v1", "title": "Vid", "artist": "Ch"}]
    with patch("app.services.sync_manager.YouTubeService") as MockYT:  # noqa: N806
        MockYT.return_value.get_artist_tracks.return_value = mock_tracks
        result = await manager._fetch_artist_tracks(wl)
    assert result == mock_tracks


@pytest.mark.asyncio
async def test_fetch_artist_tracks_unknown_source(manager):
    # source != spotify/youtube → return []
    wl = Watchlist(watch_type="artist", source="deezer", source_id="x")
    result = await manager._fetch_artist_tracks(wl)
    assert result == []


# ─── auto_sync_all_deletions ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_empty(manager, db_session):
    """No playlist watchlists → returns empty synced/skipped."""
    result = await manager.auto_sync_all_deletions(db_session, uuid.uuid4(), only_auto=False)
    assert result == {"synced": [], "skipped": []}


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_only_auto_skips_disabled(manager, db_session):
    """only_auto=True skips watchlist with auto_sync_deletions=False."""
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="P1",
        source_id="s1",
        auto_sync_deletions=False,
    )
    db_session.add(wl)
    await db_session.commit()

    result = await manager.auto_sync_all_deletions(db_session, user_id, only_auto=True)
    assert result == {"synced": [], "skipped": []}


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_safety_warning_skipped(manager, db_session):
    """Watchlist with safety_warning=True is skipped, pending report cleaned up."""
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="Risky",
        source_id="s2",
        auto_sync_deletions=True,
    )
    db_session.add(wl)
    await db_session.commit()

    token = "tok-warn"
    manager._pending_reports[token] = {}
    report = {
        "safety_warning": True,
        "warning_message": "Too many deletions",
        "sync_token": token,
    }
    manager.analyze_watchlist = AsyncMock(return_value=report)

    result = await manager.auto_sync_all_deletions(db_session, user_id, only_auto=False)

    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "Too many deletions"
    assert token not in manager._pending_reports


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_nothing_to_remove(manager, db_session):
    """to_remove_count == 0 → synced with removed_count=0, no execute_sync called."""
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="Clean",
        source_id="s3",
        auto_sync_deletions=True,
    )
    db_session.add(wl)
    await db_session.commit()

    token = "tok-empty"
    manager._pending_reports[token] = {}
    report = {"safety_warning": False, "to_remove_count": 0, "sync_token": token}
    manager.analyze_watchlist = AsyncMock(return_value=report)
    manager.execute_sync = AsyncMock()

    result = await manager.auto_sync_all_deletions(db_session, user_id, only_auto=False)

    assert result["synced"] == [{"watchlist_name": "Clean", "removed_count": 0, "files_deleted": 0}]
    manager.execute_sync.assert_not_called()
    assert token not in manager._pending_reports


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_executes_sync(manager, db_session):
    """Items to remove → execute_sync called, result appended to synced."""
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="Stale",
        source_id="s4",
        auto_sync_deletions=True,
    )
    db_session.add(wl)
    await db_session.commit()

    token = "tok-exec"
    manager._pending_reports[token] = {}
    report = {
        "safety_warning": False,
        "to_remove_count": 2,
        "sync_token": token,
        "to_remove_items": [{"track_id": "t1"}, {"track_id": "t2"}],
    }
    exec_result = {"removed_from_playlist": 2, "files_soft_deleted": 1}
    manager.analyze_watchlist = AsyncMock(return_value=report)
    manager.execute_sync = AsyncMock(return_value=exec_result)

    result = await manager.auto_sync_all_deletions(db_session, user_id, only_auto=False)

    assert result["synced"] == [{"watchlist_name": "Stale", "removed_count": 2, "files_deleted": 1}]
    manager.execute_sync.assert_called_once_with(db_session, user_id, token, ["t1", "t2"])


@pytest.mark.asyncio
async def test_auto_sync_all_deletions_exception_caught(manager, db_session):
    """Exception during per-watchlist processing → appended to skipped, others continue."""
    user_id = uuid.uuid4()
    wl = Watchlist(
        id=uuid.uuid4(),
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_name="Broken",
        source_id="s5",
        auto_sync_deletions=True,
    )
    db_session.add(wl)
    await db_session.commit()

    manager.analyze_watchlist = AsyncMock(side_effect=RuntimeError("network error"))

    result = await manager.auto_sync_all_deletions(db_session, user_id, only_auto=False)

    assert result["synced"] == []
    assert result["skipped"] == [{"watchlist_name": "Broken", "reason": "Sync failed"}]
