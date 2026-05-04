from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.schemas import UserCreate, UserLogin
from app.models.user import User
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class AuthManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_in: UserCreate) -> User:
        # Check if user exists
        result = await self.db.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        result = await self.db.execute(select(User).where(User.username == user_in.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

        # Create user
        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, user_in: UserLogin):
        # Check by email OR username
        result = await self.db.execute(
            select(User).where((User.email == user_in.email) | (User.username == user_in.email))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(user_in.password, user.hashed_password):
            return None

        return user

    def create_tokens(self, user: User):
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh_access_token(self, refresh_token: str):
        import jwt
        from app.core.config import settings
        from jwt import InvalidTokenError

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_signature": True},
            )
            token_type = payload.get("type")
            user_id = payload.get("sub")

            if token_type != "refresh":  # nosec  # noqa: S105
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token subject",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify user exists
            from uuid import UUID

            try:
                user_uuid = UUID(user_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token subject format",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from e

            result = await self.db.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Create new access and refresh tokens (Rotation)
            access_token = create_access_token(user.id)
            new_refresh_token = create_refresh_token(user.id)

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }

        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
