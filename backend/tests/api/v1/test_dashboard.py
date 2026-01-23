import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from app.api.v1.dashboard import _calculate_time_ago, _get_filename
from app.models.download import Download
from app.models.track import Track
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty(client: AsyncClient, admin_user, admin_token_headers):
    response = await client.get("/api/v1/dashboard/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_downloads"] == "0"
    assert data["tracks_in_library"] == "0"
    assert "storage_free" in data


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_data(client: AsyncClient, db_session, admin_user, admin_token_headers):
    # Add an artist and album first for FK constraints if needed,
    # but Track in this codebase seems to have optional fields or we can mock them.
    # Actually, the implementation uses Download joined with Track.

    track = Track(id=uuid.uuid4(), title="Dash Track", artist="Dash Artist")
    db_session.add(track)
    await db_session.flush()

    download = Download(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        track_id=track.id,
        status="completed",
        completed_at=datetime.now(UTC) - timedelta(hours=2),
    )
    db_session.add(download)
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tracks_in_library"] == "1"
    assert len(data["recent_activity"]) == 1
    assert data["recent_activity"][0]["title"] == "Dash Track"
    assert "2h ago" in data["recent_activity"][0]["time_ago"]


def test_calculate_time_ago():
    now = datetime.now(UTC)
    assert _calculate_time_ago(now - timedelta(minutes=5)) == "5m ago"
    assert _calculate_time_ago(now - timedelta(hours=3)) == "3h ago"
    assert _calculate_time_ago(now - timedelta(days=2)) == "2d ago"
    assert _calculate_time_ago(None) == "Just now"
    # Just now branch
    assert _calculate_time_ago(now - timedelta(seconds=10)) == "Just now"
    # Naive dt branch
    naive_dt = datetime.now()
    assert "ago" in _calculate_time_ago(naive_dt)


def test_get_filename_formatting():
    with patch("app.core.config.settings.DOWNLOAD_DIR", "C:/music"):
        dl = Download(file_path="C:/music/Artist/Album/Song.mp3")
        assert _get_filename(dl) == "Artist/Album/Song.mp3"

        dl_outside = Download(file_path="C:/other/path.mp3")
        assert _get_filename(dl_outside) == "path.mp3"

        # Exception branch
        with patch("os.path.relpath", side_effect=ValueError("Boom")):
            assert _get_filename(dl) == "Unknown"


@pytest.mark.asyncio
async def test_get_active_download_logic(client, db_session, admin_user, admin_token_headers):
    # Setup a downloading item
    track = Track(id=uuid.uuid4(), title="Active Track")
    db_session.add(track)
    await db_session.flush()
    dl = Download(id=uuid.uuid4(), user_id=admin_user.id, track_id=track.id, status="downloading", progress=50)
    db_session.add(dl)
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/stats", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["active_download"]["title"] == "Active Track"
    assert response.json()["active_download"]["progress"] == 50


def test_get_image_url_branches():
    from app.api.v1.dashboard import _get_image_url

    # No track
    assert _get_image_url(Download(track=None)) is None

    # Track with image
    t = Track(id=uuid.uuid4(), metadata_content={"image_url": "http://img"})
    assert "http://img" in _get_image_url(Download(track=t))


def test_get_storage_free_space_error():
    from app.api.v1.dashboard import _get_storage_free_space

    with patch("shutil.disk_usage", side_effect=Exception("Boom")):
        assert _get_storage_free_space() == "Unknown"


def test_get_storage_free_space_makedirs():
    from app.api.v1.dashboard import _get_storage_free_space

    with (
        patch("os.path.exists", return_value=False),
        patch("os.makedirs") as mock_makedirs,
        patch("shutil.disk_usage", return_value=(0, 0, 1024**3)),
    ):
        res = _get_storage_free_space()
        assert res == "1.0 GB"
        mock_makedirs.assert_called_once()
