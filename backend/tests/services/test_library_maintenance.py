import os
import uuid

import pytest
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.services.library_maintenance import library_maintenance_service
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_update_download_item_success(db_session: AsyncSession):
    # Setup User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="pw",
        is_active=True,
    )
    db_session.add(user)

    # Setup Track
    track = Track(title="Old Title", artist="Old Artist", duration_ms=120000)
    db_session.add(track)
    await db_session.flush()

    # Setup Download
    download_id = uuid.uuid4()
    temp_dir = os.path.abspath("temp_test_downloads")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    old_file_path = os.path.join(temp_dir, "old.mp3")
    new_file_path = os.path.join(temp_dir, "new.mp3")

    # Create dummy file
    with open(old_file_path, "w") as f:
        f.write("dummy content")

    download = Download(
        id=download_id,
        user_id=user_id,
        track_id=track.id,
        file_path=old_file_path,
        status="completed",
        source="spotify",
    )
    db_session.add(download)
    await db_session.commit()

    try:
        # Test Execution
        updates = {"filename": "new.mp3", "title": "New Title"}
        await library_maintenance_service.update_download_item(db_session, str(user_id), str(download_id), updates)

        # Verify
        await db_session.refresh(download)
        await db_session.refresh(track)

        # Check DB updates
        assert download.file_path == new_file_path
        assert track.title == "New Title"

        # Check File System updates
        assert os.path.exists(new_file_path)
        assert not os.path.exists(old_file_path)

    finally:
        # Cleanup
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_update_download_item_not_found(db_session: AsyncSession):
    user_id = str(uuid.uuid4())
    download_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="Item not found"):
        await library_maintenance_service.update_download_item(db_session, user_id, download_id, {})
