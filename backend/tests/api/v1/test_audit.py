import pytest
from httpx import AsyncClient
import uuid
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_get_audit_logs_admin(client: AsyncClient, db_session, admin_user, admin_token_headers):
    admin = admin_user
    token_headers = admin_token_headers
    # Create some logs
    log = AuditLog(
        id=uuid.uuid4(),
        action="LOGIN",
        user_id=admin.id,
        resource_type="user",
        details={"message": "Admin logged in"}
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
    from app.core.security import create_access_token
    return create_access_token(subject=user.id)

@pytest.mark.asyncio
async def test_get_audit_logs_forbidden_for_user(client: AsyncClient, user_token):
    response = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403

