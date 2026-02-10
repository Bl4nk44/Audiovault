import pytest


@pytest.mark.asyncio
async def test_add_track_to_existing_playlist_does_not_duplicate_playlist(client, admin_token_headers):
    # 1. Create a playlist
    playlist_name = "Unique Internal Playlist"
    pl_resp = await client.post(
        "/api/v1/playlists/", headers=admin_token_headers, json={"name": playlist_name, "public": False}
    )
    assert pl_resp.status_code == 201
    playlist_id = pl_resp.json()["id"]

    # 2. Add an external track (Discovery/Discovery)
    # This triggers the code path that adds to Download table and used to cause duplication
    track_id = "external:Artist:TrackForTest"

    resp = await client.post(
        f"/api/v1/playlists/{playlist_id}/tracks", headers=admin_token_headers, json={"track_ids": [track_id]}
    )
    assert resp.status_code == 201

    # 3. Check playlist list via API - should only have ONE playlist with this name
    get_resp = await client.get("/api/v1/playlists/", headers=admin_token_headers)
    assert get_resp.status_code == 200
    all_playlists = get_resp.json()
    matched_playlists = [p for p in all_playlists if p["name"] == playlist_name]

    # There should only be ONE playlist even after potential background syncs
    assert len(matched_playlists) == 1
    assert matched_playlists[0]["id"] == playlist_id
