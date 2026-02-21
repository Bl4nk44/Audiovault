"""
Direct router test for browse coverage.
"""

from unittest.mock import AsyncMock

import pytest
from app.api.subsonic.handlers.browse import get_music_folders
from app.models.user import User


@pytest.mark.asyncio
async def test_get_music_folders_direct():
    db = AsyncMock()
    user = User(id=1, username="test")

    # Direct call to the handler function
    response = await get_music_folders(f="json", current_user=user, db=db)

    # subsonic_response returns a dict for JSON format
    assert isinstance(response, dict)
    assert "subsonic-response" in response
    assert "musicFolders" in response["subsonic-response"]
