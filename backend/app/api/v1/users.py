from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_password_hash, verify_password
from fastapi import File, UploadFile
import shutil
import os
import time
from app.core.config import settings

router = APIRouter()

class UserUpdate(BaseModel):
    username: Optional[str] = None
    avatar_url: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

@router.put("/me", response_model=dict)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if user_update.username:
        # Check if username exists
        # (Implementation omitted for brevity, assuming unique constraint handles it or check manually)
        current_user.username = user_update.username
    
    if user_update.avatar_url:
        # Assuming we add avatar_url to User model or use preferences
        current_prefs = dict(current_user.preferences) if current_user.preferences else {}
        current_prefs['avatar_url'] = user_update.avatar_url
        current_user.preferences = current_prefs

    await db.commit()
    return {"status": "success", "user": {"username": current_user.username, "preferences": current_user.preferences}}

@router.put("/me/password", response_model=dict)
async def update_password_me(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    if len(password_update.new_password) < 6:
         raise HTTPException(status_code=400, detail="Password too short")

    current_user.hashed_password = get_password_hash(password_update.new_password)
    await db.commit()
    return {"status": "success"}

@router.post("/me/avatar", response_model=dict)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Create avatars directory if not exists
    avatar_dir = os.path.join(settings.DOWNLOAD_DIR, "avatars")
    if not os.path.exists(avatar_dir):
        os.makedirs(avatar_dir)
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"avatar_{current_user.id}_{int(time.time())}{file_ext}"
    file_path = os.path.join(avatar_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Construct URL (relative to backend host)
    avatar_url = f"/stream/avatars/{filename}"
    
    # Update user preferences
    current_prefs = dict(current_user.preferences) if current_user.preferences else {}
    current_prefs['avatar_url'] = avatar_url
    current_user.preferences = current_prefs
    
    await db.commit()
    
    return {"status": "success", "avatar_url": avatar_url, "user": {"username": current_user.username, "preferences": current_user.preferences}}
