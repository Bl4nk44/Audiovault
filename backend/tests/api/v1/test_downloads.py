import pytest
import uuid
from app.models.download import Download
from app.schemas.download import DownloadCreate
from app.models.track import Track

@pytest.fixture
async def sample_download(db_session, admin_user):
    trk = Track(id=uuid.uuid4(), title="Test Track", artist="Test Artist", spotify_id="sp_123")
    db_session.add(trk)
    await db_session.flush()
    
    dl = Download(
        user_id=admin_user.id,
        track_id=trk.id,
        status="pending",
        source="spotify"
    )
    db_session.add(dl)
    await db_session.commit()
    return dl

@pytest.mark.asyncio
async def test_get_downloads(client, admin_token_headers, sample_download):
    response = await client.get("/api/v1/downloads/queue", headers=admin_token_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id"] == str(sample_download.id)

@pytest.mark.asyncio
async def test_create_download(client, admin_token_headers):
    data = {
        "track_id": str(uuid.uuid4()),
        "source": "spotify",
        "playlist_name": "Test"
    }
    response = await client.post("/api/v1/downloads/add", json=data, headers=admin_token_headers)
    assert response.status_code in [200, 201]

@pytest.mark.asyncio
async def test_retry_download(client, admin_token_headers, sample_download, db_session):
    # Set status to failed
    sample_download.status = "failed"
    await db_session.commit()
    
    response = await client.post(f"/api/v1/downloads/{sample_download.id}/retry", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"



@pytest.mark.asyncio
async def test_delete_download(client, admin_token_headers, sample_download, db_session):
    response = await client.delete(f"/api/v1/downloads/{sample_download.id}", headers=admin_token_headers)
    assert response.status_code == 200
