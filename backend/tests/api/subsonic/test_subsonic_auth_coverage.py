from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.subsonic.auth import (
    create_auth_token,
    decode_hex_password,
    subsonic_auth,
    verify_token_auth,
)
from app.models.subsonic import SubsonicAuthToken
from app.models.user import User
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_decode_hex_password():
    # Valid hex
    assert decode_hex_password("enc:48656c6c6f") == "Hello"
    # Invalid hex
    assert decode_hex_password("enc:zzzz") == "enc:zzzz"
    # No prefix
    assert decode_hex_password("plain") == "plain"


@pytest.mark.asyncio
async def test_verify_token_auth_expired():
    # db is used as AsyncSession, so execute must be awaited
    db = AsyncMock()
    user = User(id=1)

    # Mock result with expired token
    expired_token = SubsonicAuthToken(
        user_id=1, token="token123", is_active=True, expires_at=datetime.now(UTC) - timedelta(days=1)
    )

    # db.execute(select(...)) is awaited
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expired_token]
    db.execute = AsyncMock(return_value=mock_result)

    result = await verify_token_auth(db, user, "any_token", "any_salt")
    assert result is False


@pytest.mark.asyncio
async def test_subsonic_auth_disabled_user():
    db = AsyncMock()
    user = User(username="disabled", is_active=False)

    with patch("app.api.subsonic.auth.get_user_by_username", return_value=user):
        with pytest.raises(HTTPException) as excinfo:
            await subsonic_auth(u="disabled", p=None, t=None, s=None, _c="test", db=db)

        assert excinfo.value.status_code == 403
        detail: dict[str, Any] = excinfo.value.detail  # type: ignore
        assert detail["subsonic-response"]["error"]["code"] == 50


@pytest.mark.asyncio
async def test_subsonic_auth_wrong_password():
    db = AsyncMock()
    user = User(username="user", is_active=True, hashed_password="hashed")

    with (
        patch("app.api.subsonic.auth.get_user_by_username", return_value=user),
        patch("app.api.subsonic.auth.verify_password", return_value=False),
    ):
        with pytest.raises(HTTPException) as excinfo:
            await subsonic_auth(u="user", p="wrong", t=None, s=None, _c="test", db=db)

        assert excinfo.value.status_code == 401
        detail: dict[str, Any] = excinfo.value.detail  # type: ignore
        assert detail["subsonic-response"]["error"]["code"] == 40


@pytest.mark.asyncio
async def test_create_auth_token_coverage():
    db = AsyncMock()
    user = User(id=1)

    # Just to cover the function and db interactions
    with patch("app.api.subsonic.auth.generate_token", return_value=("t", "s")):
        token_obj = await create_auth_token(db, user, "client", "1.0")
        assert token_obj.token == "t"
        assert token_obj.salt == "s"
        assert db.add.called
        assert db.commit.called
        assert db.refresh.called
