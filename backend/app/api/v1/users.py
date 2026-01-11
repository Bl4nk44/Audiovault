from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_password_hash, verify_password
from fastapi import File, UploadFile
import os
import time
from app.core.config import settings
from app.models.schemas import UserResponse
import aiofiles

import shutil

router = APIRouter()

@router.delete("/me", response_model=dict)
async def delete_user_me(
    delete_library: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user account.
    If delete_library is True, also deletes the user's music directory.
    """
    
    # 1. Delete physical files if requested
    if delete_library:
        # Determine user's library path
        # Default strategy: DOWNLOAD_DIR / username
        user_lib_path = os.path.join(settings.DOWNLOAD_DIR, current_user.username)
        
        # Check custom path in preferences
        # Check custom path in preferences
        if current_user.preferences and "downloadPath" in current_user.preferences:
             # custom_path = current_user.preferences["downloadPath"]
             # Security check: ensure custom_path is within allowed bounds or is strictly theirs
             # For now, we trust the preference if it was set by the app, but let's be careful.
             # If custom path is same as default user lib path, or inside it.
             # Simplest: Just nuke the default user folder if it matches username
             # If user set a custom path elsewhere, we might want to respect it OR just stick to convention.
             # Let's stick to the convention of removing the User's named directory in DOWNLOAD_DIR
             pass

        if os.path.exists(user_lib_path):
            try:
                shutil.rmtree(user_lib_path)
            except Exception as e:
                # Log error but proceed with account deletion
                print(f"Failed to delete user library: {e}")

    # 2. Delete user from DB (Cascades will handle related data)
    await db.delete(current_user)
    await db.commit()

    return {"status": "success", "message": "Account deleted"}


class UserUpdate(BaseModel):
    username: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=dict)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if user_update.username:
        # Check if username exists
        # (Implementation omitted for brevity, assuming unique constraint handles it or check manually)
        current_user.username = user_update.username

    await db.commit()
    return {
        "status": "success",
        "user": {
            "username": current_user.username,
            "preferences": current_user.preferences,
        },
    }


@router.put("/me/password", response_model=dict)
async def update_password_me(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(
        password_update.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if len(password_update.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    import hashlib
    current_user.hashed_password = get_password_hash(password_update.new_password)
    # Sync Subsonic password (MD5)
    # nosec B303: MD5 required for Subsonic Legacy Auth
    current_user.subsonic_password = hashlib.md5(password_update.new_password.encode('utf-8')).hexdigest()
    await db.commit()
    return {"status": "success"}


@router.post("/me/avatar", response_model=dict)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Create avatars directory if not exists
    # Create avatars directory if not exists
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")
    avatar_dir = os.path.join(static_dir, "avatars")
    
    if not os.path.exists(avatar_dir):
        os.makedirs(avatar_dir, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"avatar_{current_user.id}_{int(time.time())}{file_ext}"
    file_path = os.path.join(avatar_dir, filename)

    # Save file asynchronously
    async with aiofiles.open(file_path, "wb") as out_file:
        while content := await file.read(1024 * 1024):  # Read in 1MB chunks
            await out_file.write(content)

    # Construct URL (relative to backend host)
    avatar_url = f"/static/avatars/{filename}"

    # Update user preferences
    current_prefs = dict(current_user.preferences) if current_user.preferences else {}
    current_prefs["avatar_url"] = avatar_url
    current_user.preferences = current_prefs

    await db.commit()

    return {
        "status": "success",
        "avatar_url": avatar_url,
        "user": {
            "username": current_user.username,
            "preferences": current_user.preferences,
        },
    }
