import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    if response.status_code != 201:
        print(f"Register failed: {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": "password123"
    })
    
    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "username": "refreshuser",
        "password": "password123"
    })
    
    # Login to get tokens
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "refresh@example.com",
        "password": "password123"
    })
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]
    old_access_token = tokens["access_token"]
    
    import asyncio
    await asyncio.sleep(2)
    
    # Refresh
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != old_access_token
