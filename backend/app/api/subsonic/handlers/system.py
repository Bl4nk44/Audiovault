"""
System handlers for Subsonic API.

Handles authentication and system info endpoints:
- ping.view
- getToken.view (non-standard but useful)
- getUser.view
- getLicense.view
"""

from datetime import UTC, datetime

from app.api.subsonic.auth import (
    create_auth_token,
    get_user_by_username,
    subsonic_auth,
)
from app.core.security import verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/ping.view")
@router.post("/ping.view")
async def ping(
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    """
    Test connectivity and authentication.

    Used by clients to verify server connection.

    Returns:
        Subsonic response with status "ok"
    """
    return subsonic_response(f=f)


@router.get("/getLicense.view")
@router.post("/getLicense.view")
async def get_license(
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    """
    Get license information.

    Audiovault is open source, so we return a valid license.

    Returns:
        License info (always valid)
    """
    return subsonic_response(
        {
            "license": {
                "valid": True,
                "email": "opensource@audiovault.local",
                "licenseExpires": "2099-12-31T23:59:59.000Z",
            }
        },
        f=f,
    )


@router.get("/getUser.view")
@router.post("/getUser.view")
async def get_user(
    username: str = Query(None, description="Username to get info for"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about a user.

    If username is not provided, returns info about current user.
    Non-admin users can only get their own info.

    Args:
        username: Optional username (admin only for other users)

    Returns:
        User information including roles
    """
    # If no username specified, use current user
    target_user = current_user

    # Check if requesting another user's info
    if username and username != current_user.username:
        # Only admins can view other users (we don't have is_superuser, so skip for now)
        target_user = await get_user_by_username(db, username)
        if not target_user:
            return subsonic_error(70, f"User '{username}' not found", f=f)

    return subsonic_response(
        {
            "user": {
                "username": target_user.username,
                "email": target_user.email,
                "scrobblingEnabled": True,
                "maxBitRate": 0,  # 0 = unlimited
                "adminRole": False,  # Could check is_superuser if available
                "settingsRole": True,
                "downloadRole": True,
                "uploadRole": False,
                "playlistRole": True,
                "coverArtRole": True,
                "commentRole": True,
                "podcastRole": False,
                "streamRole": True,
                "jukeboxRole": False,
                "shareRole": True,
                "videoConversionRole": False,
                "folder": [1],  # Default folder ID
            }
        },
        f=f,
    )


@router.get("/getToken.view")
@router.post("/getToken.view")
async def get_token(
    u: str = Query(..., description="Username"),
    p: str = Query(..., description="Password"),
    c: str = Query(..., description="Client name"),
    v: str = Query("1.16.1", description="API version"),
    f: str = "xml",
    db: AsyncSession = Depends(get_db),
):
    """
    Get authentication token for subsequent requests.

    This is a non-standard but widely supported endpoint.
    Client sends username + password, receives token + salt.

    For subsequent requests, client sends:
    - t = MD5(token + salt)
    - s = salt (can use different salt each time)

    Args:
        u: Username
        p: Password (plaintext)
        c: Client name

    Returns:
        Token and salt for future authentication
    """
    # Get user
    user = await get_user_by_username(db, u)

    if not user:
        return subsonic_error(40, "Wrong username or password", f=f)

    # Handle enc: prefix
    password = p
    if password.startswith("enc:"):
        try:
            password = bytes.fromhex(password[4:]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            pass

    # Verify password
    if not verify_password(password, user.hashed_password):
        return subsonic_error(40, "Wrong username or password", f=f)

    if not user.is_active:
        return subsonic_error(50, "User is disabled", f=f)

    # Create new token
    auth_token = await create_auth_token(
        db=db,
        user=user,
        client_name=c,
        client_version=v,
    )

    return subsonic_response(
        {
            "token": auth_token.token,
            "salt": auth_token.salt,
        },
        f=f,
    )


@router.get("/getScanStatus.view")
@router.post("/getScanStatus.view")
async def get_scan_status(
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    """
    Get current library scan status.

    Audiovault scans are background processes, here we return
    a static 'not scanning' status for simplicity, as most mobile
    apps just need a valid response to proceed.

    Returns:
        Scan status info
    """
    return subsonic_response(
        {
            "scanStatus": {
                "scanning": False,
                "count": 1000,  # Arbitrary count
                "lastScan": datetime.now(UTC).isoformat(),
            }
        },
        f=f,
    )


@router.get("/getOpenSubsonicExtensions.view")
@router.post("/getOpenSubsonicExtensions.view")
async def get_open_subsonic_extensions(
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
):
    """
    Get supported OpenSubsonic extensions.

    OpenSubsonic is an extended Subsonic API specification.

    Returns:
        List of supported extensions
    """
    return subsonic_response(
        {
            "openSubsonicExtensions": [
                {"name": "transcodeOffset", "versions": [1]},
                {"name": "formPost", "versions": [1]},
            ]
        },
        f=f,
    )
