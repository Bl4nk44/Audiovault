import pytest
from app.services.library_data import library_data_service
from app.models.user import User
from app.models.download import Download
from app.models.track import Track
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_library_items_filtering(db_session: AsyncSession):
    # Setup User
    user_id = uuid.uuid4()
    user = User(id=user_id, email="libtest@example.com", username="testuser", hashed_password="pw", is_active=True)
    db_session.add(user)
    
    track1 = Track(title="Completed Track", artist="Artist 1", duration_ms=200000)
    track2 = Track(title="Pending Track", artist="Artist 2", duration_ms=300000)
    db_session.add(track1)
    db_session.add(track2)
    await db_session.flush()

    dl1 = Download(
        id=uuid.uuid4(), 
        user_id=user_id, 
        track_id=track1.id, 
        status="completed", 
        file_path="test.mp3"
    )
    dl1.source = "spotify"
    
    dl2 = Download(
        id=uuid.uuid4(), 
        user_id=user_id, 
        track_id=track2.id, 
        status="pending"
    )
    dl2.source = "youtube"
    
    print(f"DEBUG: dl1 source: {dl1.source}")
    print(f"DEBUG: dl2 source: {dl2.source}")
    
    db_session.add(dl1)
    db_session.add(dl2)
    # db_session.add_all([dl1, dl2])
    await db_session.commit()

    # Test Default (Completed only)
    result = await library_data_service.get_library_items(db_session, str(user_id))
    assert result["total"] == 1
    assert result["items"][0]["track"]["title"] == "Completed Track"
    
    # Test Source Filtering
    result_spotify = await library_data_service.get_library_items(db_session, str(user_id), source="spotify")
    assert result_spotify["total"] == 1
    
    result_youtube = await library_data_service.get_library_items(db_session, str(user_id), source="youtube")
    assert result_youtube["total"] == 0 # because status is pending, and get_library_items filters by completed
    
@pytest.mark.asyncio
async def test_get_queue_items_sorting(db_session: AsyncSession):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="queue@example.com", username="queueuser", hashed_password="pw", is_active=True)
    db_session.add(user)
    
    track = Track(title="T", artist="A", duration_ms=100000)
    db_session.add(track)
    await db_session.flush()
    
    # specific order: pending(3), downloading(1), processing(2), failed(4)
    # create in random order
    dl_pending = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="pending", archived=False, source="spotify")
    dl_downloading = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="downloading", archived=False, source="spotify")
    dl_processing = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="processing", archived=False, source="spotify")
    dl_failed = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="failed", archived=False, source="spotify")
    dl_archived = Download(id=uuid.uuid4(), user_id=user_id, track_id=track.id, status="completed", archived=True, source="spotify")
    
    db_session.add_all([dl_pending, dl_downloading, dl_processing, dl_failed, dl_archived])
    await db_session.commit()
    
    items = await library_data_service.get_queue_items(db_session, str(user_id))
    
    # Verify count (archived should be excluded)
    assert len(items) == 4
    
    # Verify order: downloading -> processing -> pending -> others
    statuses = [item["status"] for item in items]
    assert statuses[0] == "downloading"
    assert statuses[1] == "processing"
    assert statuses[2] == "pending"
    assert statuses[3] == "failed"

@pytest.mark.asyncio
async def test_transform_auto_fix_extension(db_session: AsyncSession):
    # Mock settings.DOWNLOAD_DIR to avoid OS errors or path issues
    with patch("app.core.config.settings.DOWNLOAD_DIR", "tmp_mock"):
        user_id = uuid.uuid4()
        track = Track(title="FixMe", artist="A")
        db_session.add(track)
        await db_session.flush()
        
        # Setup fake file system logic
        # d.file_path points to .webm, but fs only has .mp3
        download = Download(
            id=uuid.uuid4(), 
            user_id=user_id, 
            track_id=track.id, 
            status="completed", 
            file_path="tmp_mock/fake.webm",
            source="spotify"
        )
        download.track = track
        # We need to mock os.path.exists
        # If exists(/tmp/fake.webm) -> False
        # If exists(/tmp/fake.mp3) -> True
        
        with patch("os.path.exists") as mock_exists:
            def side_effect(path):
                if path == "tmp_mock/fake.webm":
                    return False
                if path == "tmp_mock/fake.mp3":
                    return True
                return False
            mock_exists.side_effect = side_effect
            
            item_data, updated = library_data_service._transform_download_item(download)
            
            assert updated is True
            assert download.file_path == "tmp_mock/fake.mp3"
            assert item_data["file_path"] == "tmp_mock/fake.mp3"

