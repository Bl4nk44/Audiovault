from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.auth_manager import AuthManager
from app.models.schemas import UserCreate, UserLogin, UserResponse, Token
from app.models.user import User
from app.core.dependencies import get_current_active_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    auth_manager = AuthManager(db)
    return await auth_manager.register_user(user_in)

@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    auth_manager = AuthManager(db)
    user = await auth_manager.authenticate_user(user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_manager.create_tokens(user)

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
