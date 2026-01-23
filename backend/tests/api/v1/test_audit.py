import uuid

import pytest
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_audit_logs_admin(client: AsyncClient, db_session, admin_user, admin_token_headers):
    admin = admin_user
    token_headers = admin_token_headers
    # Create some logs
    log = AuditLog(
        id=uuid.uuid4(), action="LOGIN", user_id=admin.id, resource_type="user", details={"message": "Admin logged in"}
    )
    db_session.add(log)
    await db_session.commit()

    response = await client.get("/api/v1/audit", headers=token_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["action"] == "LOGIN"


@pytest.fixture
async def user_token(db_session):
    # Keep user_token locally or move to global if needed.
    # For now keep checking forbid logic.
    user = User(
        id=uuid.uuid4(),
        username="user",
        email="user@example.com",
        hashed_password="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    return create_access_token(subject=user.id)


@pytest.mark.asyncio
async def test_get_audit_logs_forbidden_for_user(client: AsyncClient, user_token):
    response = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_filters(client: AsyncClient, db_session, admin_user, admin_token_headers):
    # Setup: 2 logs with different actions
    log1 = AuditLog(id=uuid.uuid4(), action="CREATE", resource_type="p", user_id=admin_user.id, details={})
    log2 = AuditLog(id=uuid.uuid4(), action="DELETE", resource_type="t", user_id=admin_user.id, details={})
    db_session.add_all([log1, log2])
    await db_session.commit()

    # Filter by action
    response = await client.get("/api/v1/audit?action=CREATE", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["action"] == "CREATE"

    # Filter by resource_type
    response = await client.get("/api/v1/audit?resource_type=t", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["resource_type"] == "t"

    # Filter by user_id
    response = await client.get(f"/api/v1/audit?user_id={admin_user.id}", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_audit_actions_and_resources(client: AsyncClient, db_session, admin_token_headers):
    response = await client.get("/api/v1/audit/actions", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    response = await client.get("/api/v1/audit/resources", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_audit_actions_forbidden(client: AsyncClient, user_token):
    response = await client.get("/api/v1/audit/actions", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403

    response = await client.get("/api/v1/audit/resources", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403
