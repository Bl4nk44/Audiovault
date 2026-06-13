from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.services.app_settings_service import (
    REGISTRATION_ENABLED_KEY,
    is_registration_enabled,
    set_registration_enabled,
)


def _new_user_payload():
    username = f"user_{uuid4().hex[:12]}"
    return {"username": username, "email": f"{username}@example.com", "password": "password123"}


@pytest.mark.asyncio
async def test_registration_enabled_by_default(db_session):
    # No row in app_settings -> defaults to enabled
    assert await is_registration_enabled(db_session) is True


@pytest.mark.asyncio
async def test_public_status_reflects_setting(client: AsyncClient, db_session):
    res = await client.get("/api/v1/auth/registration-status")
    assert res.status_code == 200
    assert res.json() == {"enabled": True}

    await set_registration_enabled(db_session, False)
    res = await client.get("/api/v1/auth/registration-status")
    assert res.json() == {"enabled": False}


@pytest.mark.asyncio
async def test_register_blocked_when_disabled(client: AsyncClient, db_session):
    await set_registration_enabled(db_session, False)
    res = await client.post("/api/v1/auth/register", json=_new_user_payload())
    assert res.status_code == 403
    assert res.json()["detail"] == "Registration is disabled"


@pytest.mark.asyncio
async def test_register_allowed_after_reenable(client: AsyncClient, db_session):
    await set_registration_enabled(db_session, False)
    await set_registration_enabled(db_session, True)
    res = await client.post("/api/v1/auth/register", json=_new_user_payload())
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_admin_can_toggle(client: AsyncClient, admin_token_headers, db_session):
    res = await client.put("/api/v1/settings/registration", json={"enabled": False}, headers=admin_token_headers)
    assert res.status_code == 200
    assert res.json() == {"enabled": False}
    assert await is_registration_enabled(db_session) is False

    res = await client.get("/api/v1/settings/registration", headers=admin_token_headers)
    assert res.status_code == 200
    assert res.json() == {"enabled": False}


@pytest.mark.asyncio
async def test_non_admin_cannot_toggle(client: AsyncClient):
    # Register a regular (non-admin) user and log in
    payload = _new_user_payload()
    await client.post("/api/v1/auth/register", json=payload)
    login = await client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.put("/api/v1/settings/registration", json={"enabled": False}, headers=headers)
    assert res.status_code == 403

    res = await client.get("/api/v1/settings/registration", headers=headers)
    assert res.status_code == 403


def test_setting_key_constant():
    assert REGISTRATION_ENABLED_KEY == "registration_enabled"


@pytest.mark.asyncio
async def test_env_killswitch_forces_disabled(client: AsyncClient, db_session, monkeypatch):
    # DB toggle says enabled, but env kill-switch overrides to off
    from app.core.config import settings

    await set_registration_enabled(db_session, True)
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", False)

    assert await is_registration_enabled(db_session) is False

    status_res = await client.get("/api/v1/auth/registration-status")
    assert status_res.json() == {"enabled": False}

    reg_res = await client.post("/api/v1/auth/register", json=_new_user_payload())
    assert reg_res.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_user_cannot_toggle(client: AsyncClient, normal_user):
    from app.core.security import create_access_token

    token = create_access_token(subject=normal_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.put("/api/v1/settings/registration", json={"enabled": False}, headers=headers)
    assert res.status_code == 403
