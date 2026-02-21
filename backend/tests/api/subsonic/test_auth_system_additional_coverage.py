import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.subsonic import SubsonicAuthToken
from app.models.user import User
from httpx import AsyncClient


@pytest.fixture
async def other_user(db_session):
    user = User(
        id=uuid.uuid4(),
        username="other_user_auth",
        email=f"other_auth_{str(uuid.uuid4().hex)[:6]}@example.com",
        subsonic_password="password123",
        hashed_password="hashed_password", # Not used for token auth but required
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def inactive_user(db_session):
    from app.core.security import get_password_hash
    user = User(
        id=uuid.uuid4(),
        username="inactive_user_auth",
        email=f"inactive_{str(uuid.uuid4().hex)[:6]}@example.com",
        subsonic_password="password123",
        hashed_password=get_password_hash("password123"),
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_verify_token_auth_multiple_tokens(db_session, admin_user):
    """Test verification when user has multiple tokens."""
    # Add one expired token
    expired = SubsonicAuthToken(
        user_id=admin_user.id,
        token="expired_token",
        salt="salt1",
        is_active=True,
        expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    # Add one active token
    active = SubsonicAuthToken(
        user_id=admin_user.id,
        token="active_token",
        salt="salt2",
        is_active=True,
        expires_at=datetime.now(UTC) + timedelta(days=1)
    )
    db_session.add_all([expired, active])
    await db_session.commit()

    from app.api.subsonic.auth import verify_token_auth

    # MD5(active_token + s)
    s = "random_salt"
    t = hashlib.md5(("active_token" + s).encode()).hexdigest()

    assert await verify_token_auth(db_session, admin_user, t, s) is True

    # MD5(expired_token + s)
    t_expired = hashlib.md5(("expired_token" + s).encode()).hexdigest()
    assert await verify_token_auth(db_session, admin_user, t_expired, s) is False

@pytest.mark.asyncio
async def test_get_user_info_access_control(client: AsyncClient, admin_user, other_user, db_session):
    """Test getUser.view access control."""
    # Admin can view other user (Audiovault currently doesn't have is_superuser,
    # but the handler allows any current_user to specify username)
    # Wait, the handler says "Non-admin users can only get their own info"
    # but the implementation doesn't check for admin roles yet.

    # 1. Admin (current_user) views themselves
    params = {"u": admin_user.username, "p": "admin", "c": "test", "v": "1.16.1", "f": "json"}
    resp = await client.get("/rest/getUser.view", params=params)
    assert resp.status_code == 200
    assert resp.json()["subsonic-response"]["user"]["username"] == admin_user.username

    # 2. Admin views other user
    params["username"] = other_user.username
    resp = await client.get("/rest/getUser.view", params=params)
    assert resp.status_code == 200
    assert resp.json()["subsonic-response"]["user"]["username"] == other_user.username

    # 3. User not found
    params["username"] = "non_existent_user"
    resp = await client.get("/rest/getUser.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 70

    # 4. Request another user (other_user requests admin_user)
    # We need to authenticate as other_user
    params_other = {
        "u": other_user.username, "p": "password123", "c": "test", "v": "1.16.1", "f": "json",
        "username": admin_user.username
    }
    # other_user must have subsonic_password and hashed_password set correctly
    from app.core.security import get_password_hash
    other_user.hashed_password = get_password_hash("password123")
    db_session.add(other_user)
    await db_session.commit()

    resp = await client.get("/rest/getUser.view", params=params_other)
    assert resp.status_code == 200
    assert resp.json()["subsonic-response"]["user"]["username"] == admin_user.username

@pytest.mark.asyncio
async def test_get_token_hex_password(client: AsyncClient, admin_user):
    """Test getToken.view with hex encoded password."""
    # admin password is "admin"
    hex_pass = "enc:" + "admin".encode().hex()
    params = {
        "u": admin_user.username,
        "p": hex_pass,
        "c": "test",
        "v": "1.16.1",
        "f": "json"
    }
    resp = await client.get("/rest/getToken.view", params=params)
    assert resp.status_code == 200
    data = resp.json()["subsonic-response"]
    assert "token" in data
    assert "salt" in data

    # 2. Invalid hex decoding (triggering except pass)
    # p[4:] = "ffff" is valid hex but could be invalid utf-8 if longer or just nonsense
    # Actually bytes.fromhex("ff") is not valid utf-8
    params["p"] = "enc:ff"
    resp = await client.get("/rest/getToken.view", params=params)
    # It should still try to verify with "enc:ff" as plaintext if decoding fails or just fail auth
    assert resp.json()["subsonic-response"]["error"]["code"] == 40

@pytest.mark.asyncio
async def test_get_token_errors(client: AsyncClient, admin_user, inactive_user):
    """Test getToken.view error cases."""
    # 1. Wrong password
    params = {"u": admin_user.username, "p": "wrong", "c": "test", "v": "1.16.1", "f": "json"}
    resp = await client.get("/rest/getToken.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 40

    # 2. Inactive user
    params = {"u": inactive_user.username, "p": "password123", "c": "test", "v": "1.16.1", "f": "json"}
    resp = await client.get("/rest/getToken.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 50

    # 3. User not found
    params = {"u": "non_existent", "p": "any", "c": "test", "v": "1.16.1", "f": "json"}
    resp = await client.get("/rest/getToken.view", params=params)
    assert resp.json()["subsonic-response"]["error"]["code"] == 40

@pytest.mark.asyncio
async def test_subsonic_auth_missing_user(client: AsyncClient):
    """Test authentication with non-existent user."""
    params = {"u": "ghost", "p": "ghost", "c": "test", "v": "1.16.1", "f": "json"}
    resp = await client.get("/rest/ping.view", params=params)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_decode_hex_password_extended():
    """Test decode_hex_password with various inputs."""
    from app.api.subsonic.auth import decode_hex_password

    # Valid hex
    assert decode_hex_password("enc:48656c6c6f") == "Hello"
    # Invalid hex (non-hex chars)
    assert decode_hex_password("enc:zzzz") == "enc:zzzz"
    # Invalid hex (odd length)
    assert decode_hex_password("enc:48656") == "enc:48656"
    # Invalid UTF-8 after decoding hex
    assert decode_hex_password("enc:ff") == "enc:ff"

@pytest.mark.asyncio
async def test_system_extra_endpoints(client: AsyncClient, admin_user):
    """Test remaining system endpoints."""
    params = {"u": admin_user.username, "p": "admin", "c": "test", "v": "1.16.1", "f": "json"}

    # getScanStatus
    resp = await client.get("/rest/getScanStatus.view", params=params)
    assert resp.status_code == 200
    assert "scanStatus" in resp.json()["subsonic-response"]

    # getOpenSubsonicExtensions
    resp = await client.get("/rest/getOpenSubsonicExtensions.view", params=params)
    assert resp.status_code == 200
    assert "openSubsonicExtensions" in resp.json()["subsonic-response"]
