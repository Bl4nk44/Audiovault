import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.download import Download
from app.models.watchlist import Watchlist
from app.services.watchlist_engine import WatchlistEngine


@pytest.fixture
def wl_engine():
    return WatchlistEngine()


@pytest.mark.asyncio
async def test_watchlist_basic_ops(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()

    # test add
    item_data = {
        "watch_type": "playlist",
        "source": "spotify",
        "source_id": "sid_123",
        "source_name": "My Playlist",
        "auto_download": False,
    }

    item = await engine.add_to_watchlist(db_session, user_id, item_data)
    assert item.source_id == "sid_123"

    # test add existing
    item2 = await engine.add_to_watchlist(db_session, user_id, item_data)
    assert item.id == item2.id

    # test get
    items = await engine.get_watchlist(db_session, user_id)
    assert len(items) == 1
    assert items[0].id == item.id

    # test update
    updated = await engine.update_watchlist_item(db_session, item.id, user_id, {"auto_download": True})
    assert updated.auto_download is True

    # test remove
    success = await engine.remove_from_watchlist(db_session, item.id, user_id)
    assert success is True

    items_after = await engine.get_watchlist(db_session, user_id)
    assert len(items_after) == 0


@pytest.mark.asyncio
async def test_handle_download_archived(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()

    # Create archived download
    download = Download(
        id=uuid.uuid4(),
        user_id=user_id,
        track_id=track_id,
        status="completed",
        archived=True,
        file_path="/tmp/test.mp3",
    )
    db_session.add(download)
    await db_session.commit()

    item = MagicMock()
    item.auto_download = True

    with patch("app.services.download_manager.download_manager.queue.put", new_callable=AsyncMock) as _mock_put:
        with patch(
            "app.services.download_manager.download_manager.start_worker", new_callable=AsyncMock
        ) as _mock_worker:
            result = await engine._handle_download(db_session, user_id, track_id, item, "Test Track")
            assert result is True
            assert download.archived is False
            assert download.status == "pending"


@pytest.mark.asyncio
async def test_check_for_updates_mocked(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()

    # Create watchlist item
    item = Watchlist(
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_id="sid_check",
        source_name="Check Playlist",
        auto_download=True,
    )
    db_session.add(item)
    await db_session.commit()

    with patch(
        "app.services.watchlist.WatchlistItemProcessor.fetch_tracks_for_item", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = [{"id": "t1", "title": "Track 1"}]

        with patch.object(engine.storage, "get_existing_download_ids", new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = set()

            with patch.object(engine.storage, "get_or_create_track", new_callable=AsyncMock) as mock_track:
                track_uuid = uuid.uuid4()
                mock_track.return_value = (track_uuid, True)

                with patch.object(engine.storage, "ensure_watchlist_item_link", new_callable=AsyncMock):
                    with patch.object(engine, "_handle_download", new_callable=AsyncMock) as mock_handle:
                        mock_handle.return_value = True

                        count = await engine.check_for_updates(db_session, user_id)
                        assert count == 1
                        mock_handle.assert_called_once()


@pytest.mark.asyncio
async def test_to_uuid_with_string(db_session: AsyncSession):
    engine = WatchlistEngine()
    str_id = str(uuid.uuid4())
    result = engine._to_uuid(str_id)
    assert isinstance(result, uuid.UUID)
    assert str(result) == str_id


@pytest.mark.asyncio
async def test_handle_download_new_auto_download(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()

    item = MagicMock()
    item.auto_download = True
    item.source = "spotify"
    item.watch_type = "playlist"
    item.source_name = "My Playlist"

    with patch("app.services.watchlist_engine.download_manager.add_download", new_callable=AsyncMock):
        result = await engine._handle_download(db_session, user_id, track_id, item, "New Track")
        assert result is True


@pytest.mark.asyncio
async def test_handle_download_no_auto_download(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()

    item = MagicMock()
    item.auto_download = False

    result = await engine._handle_download(db_session, user_id, track_id, item, "Track")
    assert result is False


@pytest.mark.asyncio
async def test_remove_watchlist_item_not_found(db_session: AsyncSession):
    engine = WatchlistEngine()
    result = await engine.remove_from_watchlist(db_session, uuid.uuid4(), uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_update_watchlist_item_not_found(db_session: AsyncSession):
    engine = WatchlistEngine()
    result = await engine.update_watchlist_item(db_session, uuid.uuid4(), uuid.uuid4(), {"auto_download": True})
    assert result is None


@pytest.mark.asyncio
async def test_add_to_watchlist_auto_download_triggers_check(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()
    item_data = {
        "watch_type": "playlist",
        "source": "spotify",
        "source_id": "sid_auto",
        "source_name": "Auto DL Playlist",
        "auto_download": True,
    }
    with patch.object(engine, "check_for_updates", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = 0
        result = await engine.add_to_watchlist(db_session, user_id, item_data)
        assert result.auto_download is True
        mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_check_for_updates_empty_tracks(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()

    item = Watchlist(
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_id="sid_empty",
        source_name="Empty Playlist",
        auto_download=True,
    )
    db_session.add(item)
    await db_session.commit()

    with patch(
        "app.services.watchlist.WatchlistItemProcessor.fetch_tracks_for_item", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = []
        count = await engine.check_for_updates(db_session, user_id)
        assert count == 0


@pytest.mark.asyncio
async def test_check_for_updates_no_source(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()

    item = Watchlist(
        user_id=user_id,
        watch_type="playlist",
        source=None,
        source_id="sid_nosource",
        source_name="No Source",
        auto_download=True,
    )
    db_session.add(item)
    await db_session.commit()

    with patch(
        "app.services.watchlist.WatchlistItemProcessor.fetch_tracks_for_item", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = [{"id": "t1", "title": "Track"}]
        count = await engine.check_for_updates(db_session, user_id)
        assert count == 0


@pytest.mark.asyncio
async def test_check_for_updates_fetch_exception(db_session: AsyncSession):
    engine = WatchlistEngine()
    user_id = uuid.uuid4()

    item = Watchlist(
        user_id=user_id,
        watch_type="playlist",
        source="spotify",
        source_id="sid_err",
        source_name="Error Playlist",
        auto_download=True,
    )
    db_session.add(item)
    await db_session.commit()

    with patch(
        "app.services.watchlist.WatchlistItemProcessor.fetch_tracks_for_item", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("Fetch failed")
        count = await engine.check_for_updates(db_session, user_id)
        assert count == 0
