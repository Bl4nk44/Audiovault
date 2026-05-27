from unittest.mock import AsyncMock, patch

import pytest

from app.services.download_manager import download_manager


@pytest.mark.asyncio
async def test_add_external_track_calls_download_manager(client, admin_token_headers):
    # 1. Create a playlist
    pl_resp = await client.post(
        "/api/v1/playlists/", headers=admin_token_headers, json={"name": "Test Mock Trigger", "public": False}
    )
    assert pl_resp.status_code == 201
    playlist_id = pl_resp.json()["id"]

    # 2. Add an external track
    track_name = "Mock Trigger Track"
    artist_name = "Mock Trigger Artist"
    track_id = f"external:{artist_name}:{track_name}"

    # We patch the instance's method. Since conftest might already have patched it,
    # we use a nested patch to ensure we capture the call in THIS test.
    with patch.object(download_manager, "add_download", new_callable=AsyncMock) as m_add:
        add_resp = await client.post(
            f"/api/v1/playlists/{playlist_id}/tracks", headers=admin_token_headers, json={"track_ids": [track_id]}
        )

        assert add_resp.status_code == 201

        # 3. Verify that add_download was called with correct data
        # It's called for each external track
        assert m_add.called
        call_args = m_add.call_args[1]
        assert call_args["download_data"].track_id is not None
        assert call_args["download_data"].source == "lastfm"
        assert call_args["download_data"].playlist_name == "Test Mock Trigger"
