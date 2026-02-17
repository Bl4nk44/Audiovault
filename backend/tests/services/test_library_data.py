import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.services.library_data import library_data_service
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_library_items_filtering(db_session: AsyncSession):
    # Setup User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="libtest@example.com",
        username="testuser",
        hashed_password="pw",
        is_active=True,
    )
    db_session.add(user)

    track1 = Track(title="Completed Track", artist="Artist 1", duration_ms=200000)
    track2 = Track(title="Pending Track", artist="Artist 2", duration_ms=300000)
    db_session.add(track1)
    db_session.add(track2)
    await db_session.flush()

    dl1 = Download(
        id=uuid.uuid4(),
        user_id=user_id,
        track_id=track1.id,
        status="completed",
        file_path="test.mp3",
    )
    dl1.source = "spotify"

    dl2 = Download(id=uuid.uuid4(), user_id=user_id, track_id=track2.id, status="pending")
    dl2.source = "youtube"

    db_session.add(dl1)
    db_session.add(dl2)
    await db_session.commit()

    # Test Default (Completed only)
    result = await library_data_service.get_library_items(db_session, str(user_id))
    assert result["total"] == 1
    assert result["items"][0]["track"]["title"] == "Completed Track"

    # Test Source Filtering
    result_spotify = await library_data_service.get_library_items(db_session, str(user_id), source="spotify")
    assert result_spotify["total"] == 1

    result_youtube = await library_data_service.get_library_items(db_session, str(user_id), source="youtube")
    assert result_youtube["total"] == 0


@pytest.mark.asyncio
async def test_get_queue_items_sorting(db_session: AsyncSession):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="queue@example.com",
        username="queueuser",
        hashed_password="pw",
        is_active=True,
    )
    db_session.add(user)

    track = Track(title="T", artist="A", duration_ms=100000)
    db_session.add(track)
    await db_session.flush()

    dl_pending = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="pending", archived=False)
    dl_downloading = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="downloading", archived=False)
    dl_processing = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="processing", archived=False)
    dl_failed = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="failed", archived=False)

    db_session.add_all([dl_pending, dl_downloading, dl_processing, dl_failed])
    await db_session.commit()

    items = await library_data_service.get_queue_items(db_session, str(user_id))
    assert len(items) == 4
    assert [i["status"] for i in items][:3] == ["downloading", "processing", "pending"]


@pytest.mark.asyncio
async def test_transform_auto_fix_extension(db_session: AsyncSession):
    with patch("app.core.config.settings.DOWNLOAD_DIR", "tmp_mock"):
        user_id = uuid.uuid4()
        track = Track(title="FixMe", artist="A")
        db_session.add(track)
        await db_session.flush()

        download = Download(
            id=uuid.uuid4(),
            user_id=user_id,
            track_id=track.id,
            status="completed",
            file_path="tmp_mock/fake.webm",
        )
        download.track = track

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda path: path == "tmp_mock/fake.mp3"
            item_data, updated = library_data_service._transform_download_item(download)
            assert updated is True
            assert download.file_path == "tmp_mock/fake.mp3"


@pytest.mark.asyncio
async def test_get_library_items_edge_cases(db_session: AsyncSession):
    # Invalid UUID
    res = await library_data_service.get_library_items(db_session, "invalid-uuid")
    assert res["total"] == 0

    user_id = uuid.uuid4()
    track = Track(id=uuid.uuid4(), title="Search Matching Title", artist="Unique Artist", duration_ms=50000)
    db_session.add(track)
    await db_session.flush()
    dl = Download(user_id=user_id, track_id=track.id, status="completed", source="s")
    dl.track = track
    db_session.add(dl)
    await db_session.commit()

    # Filters
    assert (await library_data_service.get_library_items(db_session, str(user_id), search="Matching"))["total"] == 1
    assert (await library_data_service.get_library_items(db_session, str(user_id), min_duration=60))["total"] == 0
    assert (await library_data_service.get_library_items(db_session, str(user_id), max_duration=60))["total"] == 1
    assert (await library_data_service.get_library_items(db_session, str(user_id), artist="Unique"))["total"] == 1
    assert (await library_data_service.get_library_items(db_session, str(user_id), playlist="__none__"))["total"] == 1


@pytest.mark.asyncio
async def test_get_library_items_playlist_filtered(db_session: AsyncSession):
    user_id = uuid.uuid4()
    track = Track(title="T")
    db_session.add(track)
    await db_session.flush()
    dl = Download(user_id=user_id, track_id=track.id, status="completed", playlist_name="TargetPL")
    dl.track = track
    db_session.add(dl)
    await db_session.commit()

    res = await library_data_service.get_library_items(db_session, str(user_id), playlist="TargetPL")
    assert res["total"] == 1


@pytest.mark.asyncio
async def test_get_library_items_updates_commit(db_session: AsyncSession):
    user_id = uuid.uuid4()
    track = Track(id=uuid.uuid4(), title="T")
    db_session.add(track)
    await db_session.flush()
    dl = Download(user_id=user_id, track_id=track.id, status="completed", file_path="song.webm")
    db_session.add(dl)
    await db_session.commit()

    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda p: p.endswith(".mp3")
        await library_data_service.get_library_items(db_session, str(user_id))
        assert dl.file_path is not None
        assert dl.file_path.endswith(".mp3")


@pytest.mark.asyncio
async def test_transform_path_resolution_candidate(db_session: AsyncSession):
    user_id = uuid.uuid4()
    track = Track(title="PathTest", artist="A")
    db_session.add(track)
    await db_session.flush()
    dl = Download(user_id=user_id, track_id=track.id, file_path="/app/downloads/admin/song.mp3", status="completed")
    dl.track = track

    with (
        patch("app.core.config.settings.DOWNLOAD_DIR", "C:/music"),
        patch("app.core.config.settings.API_V1_STR", "/api/v1"),
        patch("os.path.exists") as mock_exists,
        patch("os.path.relpath") as mock_relpath,
    ):
        mock_exists.side_effect = lambda p: os.path.normpath(p) == os.path.normpath("C:/music/admin/song.mp3")
        mock_relpath.side_effect = lambda path, start: (
            "admin/song.mp3" if os.path.normpath(path) == os.path.normpath("C:/music/admin/song.mp3") else "song.mp3"
        )

        item_data, _ = library_data_service._transform_download_item(dl)
        assert item_data["track"]["filename"] == "admin/song.mp3"

        # Test relpath Exception
        mock_relpath.side_effect = ValueError("err")
        item_data, _ = library_data_service._transform_download_item(dl)
        assert item_data["track"]["filename"] == "song.mp3"


def test_transform_value_error_filename():
    dl = MagicMock()
    dl.file_path = "C:/song.mp3"
    dl.track.id = uuid.uuid4()
    dl.track.metadata_content = {}

    with patch("os.path.exists", return_value=True), patch("os.path.relpath", side_effect=ValueError("cross-drive")):
        item_data, _ = library_data_service._transform_download_item(dl)
        assert item_data["track"]["filename"] == "song.mp3"


def test_transform_general_exception():
    dl = MagicMock()
    dl.file_path = "C:/song.mp3"
    dl.track.id = uuid.uuid4()
    dl.track.metadata_content = {}

    with (
        patch("os.path.exists", return_value=True),
        patch("app.core.config.settings.DOWNLOAD_DIR", "X:/dir"),
        patch("os.path.relpath", side_effect=Exception("Unexpected")),
    ):
        item_data, _ = library_data_service._transform_download_item(dl)
        assert item_data["track"]["filename"] == "song.mp3"


@pytest.mark.asyncio
async def test_get_queue_items_invalid_uuid(db_session: AsyncSession):
    res = await library_data_service.get_queue_items(db_session, "invalid-uuid")
    assert res == []
