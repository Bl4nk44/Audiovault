from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.schemas import UserCreate, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings

class AuthManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_in: UserCreate) -> User:
        # Check if user exists
        result = await self.db.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        result = await self.db.execute(select(User).where(User.username == user_in.username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Create user
        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password)
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, user_in: UserLogin):
        # Check by email OR username
        result = await self.db.execute(
            select(User).where(
                (User.email == user_in.email) | (User.username == user_in.email)
            )
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
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
