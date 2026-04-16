"""
Subsonic API authentication middleware.

Subsonic uses a unique authentication scheme:
1. Plaintext password via HTTPS (legacy, but supported by all clients)
2. MD5(password+salt) token-based auth
3. API token (for services that generated tokens via getToken)

Since Audiovault uses bcrypt (one-way hash), we can't compute MD5(password+salt)
from the stored hash. Instead, we:
1. Accept plaintext password for initial auth (HTTPS required!)
2. Generate random tokens that clients can use for subsequent requests
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.core.security import verify_password
from app.db.database import get_db
from app.models.subsonic import SubsonicAuthToken
from app.models.user import User
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Default token lifetime: 30 days
DEFAULT_TOKEN_LIFETIME_DAYS = 30


class SubsonicAuthError(Exception):
    """Raised when Subsonic authentication fails."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def generate_token() -> tuple[str, str]:
    """
    Generate a random token and salt for Subsonic auth.

    Returns:
        Tuple of (token, salt)
    """
    token = secrets.token_hex(32)  # 64 chars
    salt = secrets.token_hex(16)  # 32 chars
    return token, salt


def compute_md5_token(password: str, salt: str) -> str:
    """
    Compute MD5(password+salt) as per Subsonic spec.

    Args:
        password: The password or token
        salt: The salt value

    Returns:
        MD5 hash as hex string
    """
    # MD5 is required by Subsonic API specification for token auth
    # This is NOT used for password storage - passwords use bcrypt
    # nosemgrep: python.lang.security.audit.md5-used-as-password.md5-used-as-password, md5-used-as-password
    result = hashlib.md5(f"{password}{salt}".encode()).hexdigest()
    return result


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> User | None:
    """Get user by username or email."""
    result = await db.execute(
        select(User).where((User.username == username) | (User.email == username))
    )
    return result.scalar_one_or_none()


async def verify_token_auth(
    db: AsyncSession,
    user: User,
    client_token: str,
    client_salt: str,
) -> bool:
    """
    Verify token-based authentication.

    Client sends: t=MD5(token+s), s=salt
    We check if any of user's tokens match.

    Args:
        db: Database session
        user: User to verify
        client_token: MD5 hash from client (t parameter)
        client_salt: Salt from client (s parameter)

    Returns:
        True if authentication successful
    """
    # Get active tokens for user
    result = await db.execute(
        select(SubsonicAuthToken).where(
            and_(
                SubsonicAuthToken.user_id == user.id,
                SubsonicAuthToken.is_active,
                SubsonicAuthToken.expires_at > datetime.now(UTC),
            )
        )
    )
    tokens = result.scalars().all()

    for token_obj in tokens:
        # Compute expected hash: MD5(stored_token + client_salt)
        expected = compute_md5_token(token_obj.token, client_salt)

        if secrets.compare_digest(client_token, expected):
            # Update last used timestamp
            token_obj.last_used_at = datetime.now(UTC)
            await db.commit()
            return True

    return False


async def create_auth_token(
    db: AsyncSession,
    user: User,
    client_name: str,
    client_version: str | None = None,
    lifetime_days: int = DEFAULT_TOKEN_LIFETIME_DAYS,
) -> SubsonicAuthToken:
    """
    Create a new authentication token for a user.

    Args:
        db: Database session
        user: User to create token for
        client_name: Name of the client application
        client_version: Version of the client
        lifetime_days: Token lifetime in days

    Returns:
        Created SubsonicAuthToken
    """
    token, salt = generate_token()
    expires_at = datetime.now(UTC) + timedelta(days=lifetime_days)

    auth_token = SubsonicAuthToken(
        user_id=user.id,
        token=token,
        salt=salt,
        client_name=client_name,
        client_version=client_version,
        expires_at=expires_at,
    )

    db.add(auth_token)
    await db.commit()
    await db.refresh(auth_token)

    return auth_token


def decode_hex_password(password: str) -> str:
    """
    Decode hex-encoded password (enc: prefix).

    Some clients send passwords as: enc:48656c6c6f (hex for "Hello")

    Args:
        password: Password string, possibly with enc: prefix

    Returns:
        Decoded password
    """
    if password.startswith("enc:"):
        try:
            hex_part = password.replace("enc:", "", 1)
            return bytes.fromhex(hex_part).decode("utf-8")
        except ValueError:
            return password
    return password


async def subsonic_auth(
    u: str = Query(..., description="Username"),
    p: str | None = Query(None, description="Password (plaintext or enc:hex)"),
    t: str | None = Query(None, description="MD5(password+salt) token"),
    s: str | None = Query(None, description="Salt for token auth"),
    _c: str = Query(..., alias="c", description="Client name"),
    _v: str = Query("1.16.1", alias="v", description="API version"),
    _f: str = Query("json", alias="f", description="Response format (json/xml)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Subsonic authentication dependency.

    Supports three authentication methods:
    1. Plaintext password: p=mypassword
    2. Hex-encoded password: p=enc:6d7970617373776f7264
    3. Token-based: t=md5hash&s=salt

    Args:
        u: Username
        p: Password (plaintext or hex-encoded)
        t: Token (MD5 hash)
        s: Salt for token
        c: Client name
        v: API version
        f: Response format
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    # Get user by username
    user = await get_user_by_username(db, u)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "subsonic-response": {
                    "status": "failed",
                    "version": "1.16.1",
                    "error": {"code": 40, "message": "Wrong username or password"},
                }
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "subsonic-response": {
                    "status": "failed",
                    "version": "1.16.1",
                    "error": {"code": 50, "message": "User is disabled"},
                }
            },
        )

    auth_success = False

    # Method 1: Token-based authentication (t + s)
    # Some clients might send both t/s and p. We try token first.
    if t and s:
        auth_success = await verify_token_auth(db, user, t, s)

    # Method 2: Password-based authentication (p)
    # Include fallback: If token auth failed (or wasn't provided), but password IS provided, try password.
    if not auth_success and p:
        password = decode_hex_password(p)
        auth_success = verify_password(password, user.hashed_password)

    if not auth_success:
        logger.warning(f"Subsonic auth failed for user {u}. Token provided: {bool(t)}, Password provided: {bool(p)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "subsonic-response": {
                    "status": "failed",
                    "version": "1.16.1",
                    "error": {"code": 40, "message": "Wrong username or password"},
                }
            },
        )

    return user


# Dependency that also returns common query params
class SubsonicParams:
    """Common Subsonic request parameters."""

    def __init__(
        self,
        u: str = Query(..., description="Username"),
        c: str = Query(..., description="Client name"),
        v: str = Query("1.16.1", description="API version"),
        f: str = Query("json", description="Response format"),
    ):
        self.username = u
        self.client = c
        self.version = v
        self.format = f
