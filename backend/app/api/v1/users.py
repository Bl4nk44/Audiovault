import os
import shutil
import time
from typing import Annotated

import aiofiles
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.core.security import get_password_hash, verify_password
from app.db.database import get_db
from app.models.schemas import UserResponse
from app.models.user import User
from app.utils.sanitization import sanitize_filename
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.delete("/me", response_model=dict)
async def delete_user_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    delete_library: bool = False,
):
    """
    Delete current user account.
    If delete_library is True, also deletes the user's music directory.
    """

    # 1. Delete physical files if requested
    if delete_library:
        # Determine user's library path
        # Default strategy: DOWNLOAD_DIR / username
        sanitized_username = sanitize_filename(current_user.username)
        user_lib_path = os.path.join(settings.DOWNLOAD_DIR, sanitized_username)

        if current_user.preferences and "downloadPath" in current_user.preferences:
            # Custom download paths not supported for deletion; only default directory is removed.
            pass

        from pathlib import Path

        base_dir = Path(settings.DOWNLOAD_DIR).resolve()
        target_path = Path(user_lib_path).resolve()

        if os.path.exists(user_lib_path) and target_path.is_relative_to(base_dir) and target_path != base_dir:
            try:
                shutil.rmtree(
                    user_lib_path
                )  # nosemgrep: python.fastapi.file.tainted-path-traversal-stdlib-fastapi.tainted-path-traversal-stdlib-fastapi  # noqa: E501
            except Exception as e:
                # Log error but proceed with account deletion
                print(f"Failed to delete user library: {e}")

    # 2. Delete user from DB (Cascades will handle related data)
    await db.delete(current_user)
    await db.commit()

    return {"status": "success", "message": "Account deleted"}


class UserUpdate(BaseModel):
    username: str | None = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=dict)
async def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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


@router.put("/me/password", response_model=dict, responses={400: {"description": "Bad request"}})
async def update_password_me(
    password_update: PasswordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if len(password_update.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    import hashlib

    current_user.hashed_password = get_password_hash(password_update.new_password)
    # Sync Subsonic password (MD5) - required for Subsonic Legacy Auth
    # nosemgrep: python.lang.security.audit.md5-used-as-password.md5-used-as-password
    md5_hash = hashlib.md5(password_update.new_password.encode("utf-8")).hexdigest()  # nosec B303
    current_user.subsonic_password = md5_hash
    await db.commit()
    return {"status": "success"}


@router.post("/me/avatar", response_model=dict)
async def upload_user_avatar(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
):
    # Create avatars directory if not exists
    # Create avatars directory if not exists
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")
    avatar_dir = os.path.join(static_dir, "avatars")

    if not os.path.exists(avatar_dir):
        os.makedirs(avatar_dir, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename or "avatar.jpg")[1] or ".jpg"
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
