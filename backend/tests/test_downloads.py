import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.download import Download
from app.models.track import Track
from app.core.security import get_password_hash
import uuid
from datetime import datetime

@pytest.mark.asyncio
async def test_get_library_pagination(client: AsyncClient, db_session: AsyncSession):
    # 1. Create User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()

    # 2. Login to get token
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Seed Downloads and Tracks
    for i in range(15):
        track_id = uuid.uuid4()
        track = Track(
            id=track_id,
            title=f"Track {i}",
            artist="Test Artist",
            metadata_content={"image_url": "http://example.com/image.jpg"}
        )
        db_session.add(track)
        
        download = Download(
            id=uuid.uuid4(),
            user_id=user_id,
            track_id=track_id,
            status="completed",
            file_path=f"/tmp/track_{i}.mp3",
            created_at=datetime.utcnow()
        )
        db_session.add(download)
    await db_session.commit()

    # 4. Test Pagination
    # Page 1: Limit 10
    response = await client.get("/api/v1/downloads/library?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 10
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["items"][0]["track"]["title"] is not None

    # Page 2: Skip 10, Limit 10 (should return 5)
    response = await client.get("/api/v1/downloads/library?skip=10&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 5
    assert data["skip"] == 10
