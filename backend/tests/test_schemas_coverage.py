import uuid
from datetime import datetime
from app.models import schemas
from app.schemas.subsonic.base import SubsonicResponseWrapper


def test_base_schemas_coverage():
    # Token
    t = schemas.Token(access_token="abc", refresh_token="ref", token_type="bearer", expires_in=3600)
    assert t.access_token == "abc"

    # User
    u = schemas.UserResponse(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),  # Must be valid UUID
        username="u",
        email="e@e.com",
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )
    assert u.username == "u"

    # Track
    tr = schemas.TrackResponse(title="t", artist="a", id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"))
    assert tr.title == "t"


def test_subsonic_schemas_coverage():
    # Instantiate complex subsonic schemas to cover definitions
    s = SubsonicResponseWrapper(status="ok", version="1.16.1")
    assert s.status == "ok"
