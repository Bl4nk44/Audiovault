"""Extended tests for uncovered branches in AuthManager."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.models.schemas import UserCreate
from app.services.auth_manager import AuthManager
from fastapi import HTTPException


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def manager(mock_db):
    return AuthManager(mock_db)


def _mock_query_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ─── register_user error paths ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_email_already_registered(manager, mock_db):
    existing_user = MagicMock()
    mock_db.execute.return_value = _mock_query_result(existing_user)

    with pytest.raises(HTTPException) as exc_info:
        await manager.register_user(UserCreate(email="a@b.com", username="user", password="password123"))

    assert exc_info.value.status_code == 400
    assert "Email" in exc_info.value.detail


@pytest.mark.asyncio
async def test_register_username_already_taken(manager, mock_db):
    # First query (email) returns None, second (username) returns existing user
    mock_db.execute.side_effect = [
        _mock_query_result(None),
        _mock_query_result(MagicMock()),
    ]

    with pytest.raises(HTTPException) as exc_info:
        await manager.register_user(UserCreate(email="new@b.com", username="taken", password="password123"))

    assert exc_info.value.status_code == 400
    assert "Username" in exc_info.value.detail


# ─── refresh_access_token error paths ────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_wrong_token_type_raises_401(manager, mock_db):
    import jwt
    from app.core.config import settings

    # Create an access token (type="access") instead of refresh
    token = jwt.encode(
        {"sub": str(uuid4()), "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        await manager.refresh_access_token(token)

    assert exc_info.value.status_code == 401
    assert "token type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_no_user_id_raises_401(manager, mock_db):
    import jwt
    from app.core.config import settings

    token = jwt.encode(
        {"type": "refresh"},  # no "sub" field
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        await manager.refresh_access_token(token)

    assert exc_info.value.status_code == 401
    assert "subject" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_invalid_uuid_format_raises_401(manager, mock_db):
    import jwt
    from app.core.config import settings

    token = jwt.encode(
        {"sub": "not-a-uuid", "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        await manager.refresh_access_token(token)

    assert exc_info.value.status_code == 401
    assert "subject format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_user_not_found_raises_401(manager, mock_db):
    import jwt
    from app.core.config import settings

    user_id = str(uuid4())
    token = jwt.encode(
        {"sub": user_id, "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    mock_db.execute.return_value = _mock_query_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await manager.refresh_access_token(token)

    assert exc_info.value.status_code == 401
    assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_invalid_token_raises_401(manager, mock_db):
    with pytest.raises(HTTPException) as exc_info:
        await manager.refresh_access_token("totally.invalid.token")

    assert exc_info.value.status_code == 401
    assert "validate credentials" in exc_info.value.detail
