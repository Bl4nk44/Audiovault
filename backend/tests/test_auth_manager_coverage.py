import pytest
import uuid
import jwt
from datetime import datetime, timedelta
from app.services.auth_manager import AuthManager
from app.core.config import settings
from app.models.schemas import UserCreate, UserLogin
from app.models.user import User
from fastapi import HTTPException
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_register_user_already_exists(db_session):
    auth_manager = AuthManager(db_session)
    user_in = UserCreate(email="exists@ex.com", username="u1", password="password123")
    await auth_manager.register_user(user_in)
    
    with pytest.raises(HTTPException) as exc:
        await auth_manager.register_user(UserCreate(email="exists@ex.com", username="u2", password="password123"))
    assert exc.value.status_code == 400
    assert "Email already registered" in exc.value.detail

    with pytest.raises(HTTPException) as exc:
        await auth_manager.register_user(UserCreate(email="diff@ex.com", username="u1", password="password123"))
    assert exc.value.status_code == 400
    assert "Username already taken" in exc.value.detail

@pytest.mark.asyncio
async def test_authenticate_user_fails(db_session):
    auth_manager = AuthManager(db_session)
    user_in = UserLogin(email="none@ex.com", password="password123")
    user = await auth_manager.authenticate_user(user_in)
    assert user is None

@pytest.mark.asyncio
async def test_auth_success_and_refresh(db_session):
    auth_manager = AuthManager(db_session)
    user_in = UserCreate(email="success@ex.com", username="success", password="password123")
    user = await auth_manager.register_user(user_in)
    
    authenticated_user = await auth_manager.authenticate_user(UserLogin(email="success@ex.com", password="password123"))
    assert authenticated_user.id == user.id
    
    tokens = auth_manager.create_tokens(user)
    assert "access_token" in tokens
    
    refresh_tokens = await auth_manager.refresh_access_token(tokens["refresh_token"])
    assert "access_token" in refresh_tokens

@pytest.mark.asyncio
async def test_refresh_token_errors(db_session):
    auth_manager = AuthManager(db_session)
    
    with pytest.raises(HTTPException) as exc:
        await auth_manager.refresh_access_token("invalid_token")
    assert exc.value.status_code == 401

    token = jwt.encode({"type": "access", "sub": "123"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await auth_manager.refresh_access_token(token)
    assert "Invalid token type" in exc.value.detail

    token = jwt.encode({"type": "refresh"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await auth_manager.refresh_access_token(token)
    assert "Invalid token subject" in exc.value.detail

    token = jwt.encode({"type": "refresh", "sub": "not-a-uuid"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await auth_manager.refresh_access_token(token)
    assert "Invalid token subject format" in exc.value.detail

    token = jwt.encode({"type": "refresh", "sub": str(uuid.uuid4())}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await auth_manager.refresh_access_token(token)
    assert "User not found" in exc.value.detail
