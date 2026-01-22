import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, UTC
from app.models.download import Download
from app.models.track import Track
from app.api.v1.dashboard import _calculate_time_ago, _get_filename

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
        completed_at=datetime.now(UTC) - timedelta(hours=2)
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

def test_get_filename_formatting():
    with patch("app.core.config.settings.DOWNLOAD_DIR", "/music"):
        dl = Download(file_path="/music/Artist/Album/Song.mp3")
        assert _get_filename(dl) == "Artist/Album/Song.mp3"
        
        dl_outside = Download(file_path="/other/path.mp3")
        assert _get_filename(dl_outside) == "path.mp3"
