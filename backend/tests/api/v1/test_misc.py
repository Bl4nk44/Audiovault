import uuid

import pytest
from httpx import AsyncClient

from app.models.artist import Artist
from app.models.track import Track


@pytest.mark.asyncio
async def test_get_dashboard_stats(client: AsyncClient, admin_token_headers):
    response = await client.get("/api/v1/dashboard/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_downloads" in data
    assert "storage_free" in data


@pytest.mark.asyncio
async def test_record_history(client: AsyncClient, admin_token_headers, db_session):
    # Create track
    track_id = uuid.uuid4()
    track = Track(id=track_id, title="History Track", spotify_id=f"hist_{uuid.uuid4()}")
    db_session.add(track)
    await db_session.commit()

    payload = {"track_id": str(track_id), "duration_played": 120}
    response = await client.post("/api/v1/history/record", headers=admin_token_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_record_history_not_found(client: AsyncClient, admin_token_headers):
    payload = {"track_id": str(uuid.uuid4()), "duration_played": 120}
    response = await client.post("/api/v1/history/record", headers=admin_token_headers, json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_artists(client: AsyncClient):
    response = await client.get("/api/v1/artists/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_artist_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/artists/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_artist_success(client: AsyncClient, db_session):
    artist_id = uuid.uuid4()
    artist = Artist(id=artist_id, name="Test Artist")
    db_session.add(artist)
    await db_session.commit()

    response = await client.get(f"/api/v1/artists/{artist_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Artist"
