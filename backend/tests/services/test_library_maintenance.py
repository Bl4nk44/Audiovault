import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.download import Download
from app.models.track import Track
from app.services.library_maintenance import library_maintenance_service

UID1 = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_fix_legacy_data_heuristics(db_session: AsyncSession):
    # Setup downloads with different triggers
    t_spot = Track(id=uuid.uuid4(), title="S", spotify_id="spot1")
    t_deezer = Track(id=uuid.uuid4(), title="D", deezer_id="deezer1")
    t_yt = Track(id=uuid.uuid4(), title="Y", youtube_id="yt1")
    t_apple = Track(id=uuid.uuid4(), title="A", metadata_content={"apple_music_id": "apple1"})
    t_meta = Track(id=uuid.uuid4(), title="M", metadata_content={"source": "Tidal"})

    db_session.add_all([t_spot, t_deezer, t_yt, t_apple, t_meta])
    await db_session.flush()

    user_id = uuid.uuid4()
    d1 = Download(user_id=user_id, track_id=t_spot.id, source="", status="completed")
    d2 = Download(user_id=user_id, track_id=t_deezer.id, source=None, status="completed")
    d3 = Download(user_id=user_id, track_id=t_yt.id, source="other", status="completed")
    d4 = Download(user_id=user_id, track_id=t_apple.id, source="", status="completed")
    d5 = Download(user_id=user_id, track_id=t_meta.id, source="", status="completed")

    db_session.add_all([d1, d2, d3, d4, d5])
    await db_session.commit()

    count = await library_maintenance_service.fix_legacy_data(db_session)
    assert count == 5
    assert d1.source == "spotify"
    assert d2.source == "deezer"
    assert d3.source == "youtube"
    assert d4.source == "apple_music"
    assert d5.source == "tidal"


@pytest.mark.asyncio
async def test_rescan_library_integrity(db_session: AsyncSession):
    user_id = uuid.uuid4()
    dl = Download(user_id=user_id, track_id=uuid.uuid4(), status="completed", file_path="missing.mp3")
    db_session.add(dl)
    await db_session.commit()

    with (
        patch("os.path.exists", return_value=False),
        patch("app.services.library_maintenance.download_manager", new_callable=AsyncMock) as mock_dm,
    ):
        mock_dm.queue = AsyncMock()
        count = await library_maintenance_service.rescan_library_integrity(db_session, str(user_id))
        assert count == 1
        assert dl.status == "pending"


@pytest.mark.asyncio
async def test_clear_history_migration_catch(db_session: AsyncSession):
    user_id = uuid.uuid4()
    # Mock execute to simulate ALTER TABLE error
    with patch.object(db_session, "execute", side_effect=[Exception("Already exists"), AsyncMock()]):
        await library_maintenance_service.clear_history(db_session, str(user_id))
        # Should rollback and continue to update stmt


@pytest.mark.asyncio
async def test_update_download_item_rename(db_session: AsyncSession):
    user_id = uuid.uuid4()
    track = Track(title="Old", artist="A")
    db_session.add(track)
    await db_session.flush()
    dl = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, file_path="C:/old.mp3")
    dl.track = track
    db_session.add(dl)
    await db_session.commit()

    with patch("os.path.exists", return_value=True), patch("os.rename") as mock_rename:
        await library_maintenance_service.update_download_item(
            db_session, str(user_id), str(dl.id), {"filename": "new.mp3", "title": "New"}
        )
        assert dl.track.title == "New"
        mock_rename.assert_called_once()


@pytest.mark.asyncio
async def test_maintenance_invalid_uuids(db_session: AsyncSession):
    assert await library_maintenance_service.rescan_library_integrity(db_session, "bad") == 0
    await library_maintenance_service.clear_history(db_session, "bad")  # No return
    with pytest.raises(ValueError, match="Invalid UUID format"):
        await library_maintenance_service.update_download_item(db_session, "bad", str(uuid.uuid4()), {})

    with pytest.raises(ValueError, match="Item not found"):
        await library_maintenance_service.update_download_item(db_session, str(uuid.uuid4()), str(uuid.uuid4()), {})


@pytest.mark.asyncio
async def test_update_download_item_rename_fail(db_session: AsyncSession):
    user_id = uuid.uuid4()
    dl = Download(id=uuid.uuid4(), user_id=user_id, track_id=uuid.uuid4(), file_path="C:/old.mp3")
    db_session.add(dl)
    await db_session.commit()
    with (
        patch("app.core.dependencies.get_db"),
        patch.object(db_session, "execute", return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=dl))),
        patch("os.path.exists", return_value=True),
        patch("os.rename", side_effect=Exception("Perm error")),
    ):
        with pytest.raises(ValueError, match="Failed to rename file"):
            await library_maintenance_service.update_download_item(
                db_session, str(user_id), str(dl.id), {"filename": "new.mp3"}
            )


@pytest.mark.asyncio
async def test_rescan_library_integrity_no_path(db_session: AsyncSession):
    user_id = uuid.uuid4()
    dl = Download(user_id=user_id, track_id=uuid.uuid4(), status="completed", file_path=None)
    db_session.add(dl)
    await db_session.commit()

    with patch("app.services.library_maintenance.download_manager", new_callable=AsyncMock) as mock_dm:
        mock_dm.queue = AsyncMock()
        count = await library_maintenance_service.rescan_library_integrity(db_session, str(user_id))
        assert count == 1


@pytest.mark.asyncio
async def test_clear_history_migration_success(db_session: AsyncSession):
    user_id = uuid.uuid4()
    # First call to execute (ALTER TABLE) succeeds
    # Second call to execute (UPDATE) succeeds
    with patch.object(db_session, "execute", new_callable=AsyncMock) as mock_exec:
        await library_maintenance_service.clear_history(db_session, str(user_id))
        assert mock_exec.call_count >= 2


@pytest.mark.asyncio
async def test_update_download_item_all_metadata(db_session: AsyncSession):
    user_id = uuid.uuid4()
    track = Track(title="Old", artist="OldA", album="OldAlb")
    db_session.add(track)
    await db_session.flush()
    dl = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id)
    dl.track = track
    db_session.add(dl)
    await db_session.commit()

    await library_maintenance_service.update_download_item(
        db_session, str(user_id), str(dl.id), {"artist": "NewA", "album": "NewAlb"}
    )
    assert dl.track.artist == "NewA"
    assert dl.track.album == "NewAlb"
