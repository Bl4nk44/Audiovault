import jwt
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_signature": True})
        user_id_raw = payload.get("sub")
        token_type_raw = payload.get("type")

        if not isinstance(user_id_raw, str) or not isinstance(token_type_raw, str):
            raise credentials_exception

        user_id: str = user_id_raw
        token_type: str = token_type_raw

        if token_type != "access":  # nosec
            raise credentials_exception
    except InvalidTokenError as e:
        raise credentials_exception from e

    from uuid import UUID

    try:
        user_uuid = UUID(user_id)
    except ValueError as e:
        raise credentials_exception from e

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
