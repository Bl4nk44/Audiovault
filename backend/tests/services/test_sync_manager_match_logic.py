import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.track import Track
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.services.sync_manager import SyncManager


@pytest.fixture
def sync_manager():
    return SyncManager()


@pytest.mark.asyncio
async def test_analyze_watchlist_safety_warnings(sync_manager):
    # Setup: 100 local items, remove 30 (30% > 10% threshold)
    watchlist_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_db = AsyncMock()
    # Mock watchlist
    mock_db.execute.return_value.scalar_one_or_none.return_value = Watchlist(
        id=watchlist_id, user_id=user_id, source="spotify", source_name="PL", watch_type="playlist", source_id="src1"
    )

    # Mock local items (100 items)
    local_items = []
    for i in range(100):
        t = Track(id=str(uuid.uuid4()), title=f"T{i}", spotify_id=f"loc{i}")
        local_items.append(WatchlistItem(watchlist_id=watchlist_id, track=t))

    mock_db.execute.side_effect = [
        MagicMock(
            scalar_one_or_none=MagicMock(
                return_value=Watchlist(
                    id=watchlist_id,
                    user_id=user_id,
                    source="spotify",
                    source_name="PL",
                    watch_type="playlist",
                    source_id="src1",
                )
            )
        ),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=local_items)))),
    ]

    # Mock remote tracks (only 70 matching)
    remote_tracks = [{"id": f"loc{i}", "title": f"T{i}", "artist": "A"} for i in range(70)]

    with patch.object(SyncManager, "_fetch_remote_tracks", new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = remote_tracks

        report = await sync_manager.analyze_watchlist(mock_db, user_id, watchlist_id)

        assert report["safety_warning"] is True
        # It could be high deletion ratio OR massive deletion depending on order or logic.
        # Since 30 > 20, "Massive deletion" is also triggered.
        # The code might overwrite the message.
        assert "deletion" in report["warning_message"]
        assert report["to_remove_count"] == 30


@pytest.mark.asyncio
async def test_analyze_watchlist_matching_logic(sync_manager):
    # Test matching by youtube_id and metadata
    w_id = str(uuid.uuid4())
    u_id = str(uuid.uuid4())

    # Track 1: Matching via youtube_id (Source=youtube)
    t1 = Track(id=str(uuid.uuid4()), title="T1", youtube_id="yt1")
    # Track 2: Matching via metadata (Source=deezer)
    t2 = Track(id=str(uuid.uuid4()), title="T2", metadata_content={"deezer_id": "dz1"})
    # Track 3: No match
    t3 = Track(id=str(uuid.uuid4()), title="T3")

    local_items = [WatchlistItem(track=t1), WatchlistItem(track=t2), WatchlistItem(track=t3)]

    # Helper to run analysis relative to source type
    async def run_analysis(source, remote_ids):
        mock_db = AsyncMock()
        wl = Watchlist(id=w_id, user_id=u_id, source=source, watch_type="playlist", source_id="s")
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=wl)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=local_items)))),
        ]

        remote = [{"id": rid, "title": "X", "artist": "Y"} for rid in remote_ids]

        with patch.object(SyncManager, "_fetch_remote_tracks", new_callable=AsyncMock) as m_fetch:
            m_fetch.return_value = remote
            return await sync_manager.analyze_watchlist(mock_db, u_id, w_id)

    # Case 1: Youtube Source
    report_yt = await run_analysis("youtube", ["yt1"])
    # t1 should match (kept), t2/t3 removed
    removals_yt = [x["track_id"] for x in report_yt["to_remove_items"]]
    assert str(t1.id) not in removals_yt
    assert str(t3.id) in removals_yt

    # Case 2: Deezer Source (Metadata check)
    report_dz = await run_analysis("deezer", ["dz1"])
    # t2 should match, t1/t3 removed
    removals_dz = [x["track_id"] for x in report_dz["to_remove_items"]]
    assert str(t2.id) not in removals_dz
    assert str(t3.id) in removals_dz


@pytest.mark.asyncio
async def test_fetch_remote_tracks_strategies(sync_manager):
    # 1. Playlist via Provider
    wl_pl = Watchlist(watch_type="playlist", source="spotify", source_id="pl1")
    with patch("app.services.sync_manager.provider_manager.get_provider_by_name") as m_get_prov:
        mock_prov = AsyncMock()
        mock_prov.extract_playlist.return_value.tracks = [MagicMock(source_id="t1", title="Tit", artist="Art")]
        m_get_prov.return_value = mock_prov

        tracks = await sync_manager._fetch_remote_tracks(wl_pl)
        assert len(tracks) == 1
        assert tracks[0]["id"] == "t1"

    # 2. Artist via SpotifyService (Legacy)
    wl_ar = Watchlist(watch_type="artist", source="spotify", source_id="ar1")
    with patch("app.services.sync_manager.SpotifyService") as MockSpot:
        inst = AsyncMock()
        MockSpot.return_value = inst
        inst.get_artist_albums.return_value = [{"id": "al1"}]
        inst.get_album_tracks.return_value = [
            {"id": "t2", "name": "T2", "artists": [{"name": "A"}]}
        ]  # _format_track output mock

        # Need to adjust because _fetch_remote_tracks expects dicts from get_album_tracks
        # The real service returns formatted dicts.

        tracks_ar = await sync_manager._fetch_remote_tracks(wl_ar)
        assert len(tracks_ar) == 1
        assert tracks_ar[0]["id"] == "t2"


@pytest.mark.asyncio
async def test_fetch_remote_tracks_error(sync_manager):
    wl = Watchlist(watch_type="playlist", source="spotify", source_id="pl1")
    with patch("app.services.sync_manager.provider_manager.get_provider_by_name", side_effect=Exception("API Fail")):
        tracks = await sync_manager._fetch_remote_tracks(wl)
        assert tracks == []
