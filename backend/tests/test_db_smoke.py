import pytest
from app.models.download import Download

@pytest.mark.asyncio
async def test_smoke_insert(db_session):
    print("Smoking DB...")
    try:
        d = Download(source="test", status="pending")
        db_session.add(d)
        await db_session.commit()
        print("Success!")
        assert d.id is not None
    except Exception as e:
        print(f"Failed: {e}")
        raise e
