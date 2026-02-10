from unittest.mock import AsyncMock, patch

import pytest
from app.services.download_manager import download_manager


@pytest.mark.asyncio
async def test_add_duplicate_track_reports_duplicate(client, admin_token_headers):
    # 1. Create a playlist
    pl_resp = await client.post(
        "/api/v1/playlists/", headers=admin_token_headers, json={"name": "Test Duplicate", "public": False}
    )
    assert pl_resp.status_code == 201
    playlist_id = pl_resp.json()["id"]

    # 2. Add an external track for the first time
    track_id = "external:Artist:Track"

    with patch.object(download_manager, "add_download", new_callable=AsyncMock):
        # First addition
        resp1 = await client.post(
            f"/api/v1/playlists/{playlist_id}/tracks", headers=admin_token_headers, json={"track_ids": [track_id]}
        )
        assert resp1.status_code == 201
        assert resp1.json()["added_count"] == 1
        assert resp1.json()["duplicate_count"] == 0

        # Second addition (duplicate)
        resp2 = await client.post(
            f"/api/v1/playlists/{playlist_id}/tracks", headers=admin_token_headers, json={"track_ids": [track_id]}
        )
        assert resp2.status_code == 201
        assert resp2.json()["added_count"] == 0
        assert resp2.json()["duplicate_count"] == 1
        assert resp2.json()["total_processed"] == 1
