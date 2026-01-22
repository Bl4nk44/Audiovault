import pytest
import os
import uuid
import io
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.user import User
from app.core.security import get_password_hash

@pytest.fixture
async def sample_user(db_session):
    user = User(
        id=uuid.uuid4(),
        username="testuser_api",
        email="test_api@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token_headers):
    response = await client.get("/api/v1/users/me", headers=admin_token_headers)
    assert response.status_code == 200
    assert "username" in response.json()

@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, admin_token_headers):
    payload = {"username": "new_username"}
    response = await client.put("/api/v1/users/me", headers=admin_token_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "new_username"

@pytest.mark.asyncio
async def test_update_password(client: AsyncClient, admin_token_headers):
    payload = {
        "current_password": "admin",
        "new_password": "new_secure_password"
    }
    response = await client.put("/api/v1/users/me/password", headers=admin_token_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_update_password_short(client: AsyncClient, admin_token_headers):
    payload = {
        "current_password": "admin",
        "new_password": "123"
    }
    response = await client.put("/api/v1/users/me/password", headers=admin_token_headers, json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Password too short"

@pytest.mark.asyncio
async def test_upload_avatar(client: AsyncClient, admin_token_headers):
    # Mocking aiofiles and os.makedirs/exists
    file_content = b"fake image content"
    files = {"file": ("avatar.jpg", io.BytesIO(file_content), "image/jpeg")}
    
    with patch("os.path.exists", return_value=True), \
         patch("app.api.v1.users.aiofiles.open", new_callable=MagicMock) as mock_open:
        
        mock_file = AsyncMock()
        mock_file.__aenter__.return_value = mock_file
        mock_open.return_value = mock_file
        
        response = await client.post("/api/v1/users/me/avatar", headers=admin_token_headers, files=files)
        assert response.status_code == 200
        assert "avatar_url" in response.json()

@pytest.mark.asyncio
async def test_delete_me(client: AsyncClient, db_session):
    # Use a separate user to avoid deleting the admin used for headers
    username = f"to_delete_{uuid.uuid4().hex[:8]}"
    user = User(
        id=uuid.uuid4(),
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    # We need a token for THIS user
    from app.core.security import create_access_token
    from datetime import timedelta
    access_token = create_access_token(subject=user.id, expires_delta=timedelta(minutes=15))
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Narrowly patch os.path.exists ONLY inside the route handler if possible, 
    # or ensure it returns True only for specific paths to not break JWT/internal files
    with patch("app.api.v1.users.os.path.exists", return_value=True), \
         patch("app.api.v1.users.shutil.rmtree") as mock_rm:
        response = await client.delete("/api/v1/users/me", params={"delete_library": True}, headers=headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Account deleted"
        assert mock_rm.called
