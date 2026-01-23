import pytest
from app.models.download import Download


@pytest.mark.asyncio
async def test_smoke_insert(db_session):
    print("Smoking DB...")
    from app.models.track import Track
    from app.models.user import User
    import uuid
    
    user = User(id=uuid.uuid4(), username="smoke", email="smoke@example.com", hashed_password="x")
    track = Track(id=uuid.uuid4(), title="Smoke")
    db_session.add(user)
    db_session.add(track)
    await db_session.flush()

    try:
        d = Download(id=uuid.uuid4(), source="test", status="pending", user_id=user.id, track_id=track.id)
        db_session.add(d)
        await db_session.commit()
        print("Success!")
        assert d.id is not None
    except Exception as e:
        print(f"Failed: {e}")
        raise e
