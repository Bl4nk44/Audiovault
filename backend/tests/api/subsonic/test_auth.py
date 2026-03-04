import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from app.core.security import get_password_hash
from app.models.subsonic import SubsonicAuthToken
from app.models.user import User
from httpx import AsyncClient
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        username="testuser", email="test@example.com", hashed_password=get_password_hash("testpass"), is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_ping_no_auth(client: AsyncClient):
    response = await client.get("/rest/ping.view?u=nonexistent&p=wrong&c=test&v=1.16.1&f=json")
    assert response.status_code == 401
    data = response.json()
    # FastAPI wraps error detail in "detail" key
    sub_resp = data["detail"]["subsonic-response"]
    assert sub_resp["status"] == "failed"
    assert sub_resp["error"]["code"] == 40


@pytest.mark.asyncio
async def test_ping_plaintext_auth(client: AsyncClient, test_user: User):
    response = await client.get("/rest/ping.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_ping_token_auth(client: AsyncClient, test_user: User, db_session: AsyncSession):
    # Create a token
    token_val = "secret_token_val"
    salt = "somesalt"
    auth_token = SubsonicAuthToken(
        user_id=test_user.id, token=token_val, salt=salt, expires_at=datetime.now(UTC) + timedelta(days=1)
    )
    db_session.add(auth_token)
    await db_session.commit()

    # MD5(token + salt_from_request)
    req_salt = "reqsalt"
    token_hash = hashlib.md5(f"{token_val}{req_salt}".encode()).hexdigest()

    response = await client.get(f"/rest/ping.view?u=testuser&t={token_hash}&s={req_salt}&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_get_token(client: AsyncClient, test_user: User):
    response = await client.get("/rest/getToken.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "token" in data["subsonic-response"]
    assert "salt" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_subsonic_auth_inactive_user(client: AsyncClient, db_session: AsyncSession):
    inactive_user = User(
        username="inactive", email="inactive@example.com", hashed_password=get_password_hash("pass"), is_active=False
    )
    db_session.add(inactive_user)
    await db_session.commit()

    response = await client.get("/rest/ping.view?u=inactive&p=pass&c=test&v=1.16.1&f=json")
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["subsonic-response"]["error"]["code"] == 50


@pytest.mark.asyncio
async def test_subsonic_auth_hex_password(client: AsyncClient, test_user: User):
    # 'testpass' encoded in hex is 7465737470617373
    hex_pass = "7465737470617373"
    response = await client.get(f"/rest/ping.view?u=testuser&p=enc:{hex_pass}&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_subsonic_auth_invalid_hex_password(client: AsyncClient, test_user: User):
    # Invalid hex string
    response = await client.get("/rest/ping.view?u=testuser&p=enc:not_hex_at_all&c=test&v=1.16.1&f=json")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subsonic_auth_invalid_token(client: AsyncClient, test_user: User):
    response = await client.get("/rest/ping.view?u=testuser&t=invalidhash&s=somesalt&c=test&v=1.16.1&f=json")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subsonic_auth_expired_token(client: AsyncClient, test_user: User, db_session: AsyncSession):
    token_val = "expired_token_val"
    salt = "expiredsalt"
    auth_token = SubsonicAuthToken(
        user_id=test_user.id, token=token_val, salt=salt, expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    db_session.add(auth_token)
    await db_session.commit()

    req_salt = "reqsalt"
    token_hash = hashlib.md5(f"{token_val}{req_salt}".encode()).hexdigest()

    response = await client.get(f"/rest/ping.view?u=testuser&t={token_hash}&s={req_salt}&c=test&v=1.16.1&f=json")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subsonic_auth_error_class():
    from app.api.subsonic.auth import SubsonicAuthError
    err = SubsonicAuthError(40, "Test error")
    assert err.code == 40
    assert err.message == "Test error"


@pytest.mark.asyncio
async def test_subsonic_params_class():
    from app.api.subsonic.auth import SubsonicParams
    params = SubsonicParams(u="user", c="client", v="1.0", f="xml")
    assert params.username == "user"
    assert params.client == "client"
    assert params.version == "1.0"
    assert params.format == "xml"


@pytest.mark.asyncio
async def test_create_auth_token_coverage(db_session: AsyncSession, test_user: User):
    from app.api.subsonic.auth import create_auth_token
    token_obj = await create_auth_token(db_session, test_user, "test-client")
    assert token_obj.token is not None
    assert token_obj.client_name == "test-client"
    assert token_obj.user_id == test_user.id


@pytest.mark.asyncio
async def test_verify_token_auth_no_tokens(db_session: AsyncSession, test_user: User):
    from app.api.subsonic.auth import verify_token_auth
    result = await verify_token_auth(db_session, test_user, "sometoken", "somesalt")
    assert result is False


@pytest.mark.asyncio
async def test_subsonic_auth_explicit_call(db_session: AsyncSession, test_user: User):
    from app.api.subsonic.auth import subsonic_auth
    # Success case
    user = await subsonic_auth(u="testuser", p="testpass", _c="test", db=db_session)
    assert user.id == test_user.id

    # Invalid user
    with pytest.raises(HTTPException) as exc:
        await subsonic_auth(u="nonexistent", _c="test", db=db_session)
    assert exc.value.status_code == 401

    # Inactive user
    test_user.is_active = False
    db_session.add(test_user)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await subsonic_auth(u="testuser", p="testpass", _c="test", db=db_session)
    assert exc.value.status_code == 403
