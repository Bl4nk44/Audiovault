import uuid
from datetime import datetime

import pytest
from app.core.security import create_access_token
from app.models.download import Download
from app.models.user import User
from httpx import AsyncClient


@pytest.fixture
async def auth_token(db_session):
    user = User(id=uuid.uuid4(), username="storage_tester", email="storage@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.commit()
    return create_access_token(subject=user.id), user


@pytest.mark.asyncio
async def test_get_storage_stats(client: AsyncClient, db_session, auth_token):
    token, user = auth_token

    # Seed downloads
    d1 = Download(
        id=uuid.uuid4(),
        user_id=user.id,
        track_id=uuid.uuid4(),
        status="completed",
        file_path="song1.mp3",
        source="youtube",
        playlist_name="My Playlist",
        created_at=datetime.now(),
    )
    db_session.add(d1)
    await db_session.commit()

    # Mocking get_file_size internal function or os.path.getsize to return valid size
    # since song1.mp3 doesn't exist.
    # We patch inside the module where it is used: app.api.v1.storage
    from unittest.mock import patch

    with patch("app.api.v1.storage.get_file_size", return_value=1024 * 1024):  # 1 MB
        response = await client.get("/api/v1/storage/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 1
    assert data["total_size_bytes"] == 1024 * 1024
    assert data["by_source"]["youtube"]["count"] == 1
    assert data["by_playlist"]["My Playlist"]["count"] == 1
