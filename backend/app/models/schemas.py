from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Token
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# User
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str  # Can be email or username
    password: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    preferences: dict = {}

    class Config:
        from_attributes = True


# Track (Placeholder for now)
class TrackBase(BaseModel):
    title: str
    artist: str


class TrackResponse(TrackBase):
    id: UUID
    duration_ms: int | None = None

    class Config:
        from_attributes = True
