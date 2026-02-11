import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from app.core.config import settings
from app.core.dependencies import get_current_active_user, get_current_user
from app.models.user import User
from fastapi import HTTPException


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_type(mock_db):
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "refresh"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token, mock_db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_payload(mock_db):
    token = jwt.encode({"sub": 123, "type": True}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token, mock_db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_uuid(mock_db):
    token = jwt.encode(
        {"sub": "not-a-uuid", "type": "access"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token, mock_db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found(mock_db):
    user_id = str(uuid.uuid4())
    token = jwt.encode({"sub": user_id, "type": "access"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token, mock_db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    mock_user = MagicMock(spec=User)
    mock_user.is_active = False

    with pytest.raises(HTTPException) as exc:
        await get_current_active_user(mock_user)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Inactive user"


@pytest.mark.asyncio
async def test_get_current_active_user_active():
    mock_user = MagicMock(spec=User)
    mock_user.is_active = True

    result = await get_current_active_user(mock_user)
    assert result == mock_user
