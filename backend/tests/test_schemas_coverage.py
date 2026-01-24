from app.schemas import schemas
from app.schemas.subsonic import ResponseStatus, SubsonicResponse


def test_base_schemas_coverage():
    # Token
    t = schemas.Token(access_token="abc", token_type="bearer")
    assert t.access_token == "abc"

    # User
    u = schemas.User(id="123", username="u", email="e", is_active=True, is_superuser=False)
    assert u.username == "u"

    # Track
    tr = schemas.Track(id="1", title="t", duration=100)
    assert tr.title == "t"


def test_subsonic_schemas_coverage():
    # Instantiate complex subsonic schemas to cover definitions
    s = ResponseStatus(status="ok", version="1.16.1")
    assert s.status == "ok"
    r = SubsonicResponse(status="ok", version="1.16.1", type="audiovault")
    assert r.status == "ok"
