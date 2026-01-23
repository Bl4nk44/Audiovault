from uuid import uuid4

import pytest
from httpx import AsyncClient

# NOTE: We assume 'client' fixture is available from conftest.py
# and it uses the test database where we can seed a user.


@pytest.mark.asyncio
async def test_login_access_token(client: AsyncClient, db_session, admin_user):
    # Ensure admin_user is in DB (provided by fixture usually, or create here if needed)
    # The 'admin_user' fixture typically creates a user with password "admin"

    # Check AuthManager.authenticate_user implementation.
    # v1/auth.py uses UserLogin schema -> username field.

    response = await client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "admin"})
    assert response.status_code == 200, response.json()
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_access_token_failure(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={"email": "wronguser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user):
    # First login to get refresh token
    login_res = await client.post("/api/v1/auth/login", json={"email": admin_user.username, "password": "admin"})
    refresh_token = login_res.json()["refresh_token"]

    # Use refresh token
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    username = f"newuser_{uuid4()}"
    email = f"{username}@example.com"
    data = {"username": username, "email": email, "password": "password123"}

    response = await client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201
    created_user = response.json()
    assert created_user["username"] == username
    assert created_user["email"] == email
    assert "id" in created_user


@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, admin_token_headers):
    response = await client.get("/api/v1/auth/me", headers=admin_token_headers)
    assert response.status_code == 200
    assert "id" in response.json()
