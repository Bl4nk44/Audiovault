from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.db.init_data import init_db
from app.models.user import User


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_init_db_creates_admin(mock_db):
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: None))

    mock_settings = MagicMock()
    mock_settings.ADMIN_USERNAME = "admin"
    mock_settings.ADMIN_EMAIL = "admin@example.com"
    mock_settings.ADMIN_PASSWORD = "secret_password"

    with patch("app.core.config.settings", mock_settings):
        await init_db(mock_db)

        # Verify db.add was called with a User object
        assert mock_db.add.called
        args, _ = mock_db.add.call_args
        user = args[0]
        assert isinstance(user, User)
        assert user.username == "admin"
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_init_db_admin_exists(mock_db):
    mock_user = MagicMock(spec=User)
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: mock_user))

    await init_db(mock_db)
    assert not mock_db.add.called


@pytest.mark.asyncio
async def test_init_db_generates_password(mock_db):
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: None))

    mock_settings = MagicMock()
    mock_settings.ADMIN_USERNAME = "admin"
    mock_settings.ADMIN_EMAIL = "admin@example.com"
    mock_settings.ADMIN_PASSWORD = None  # Force generation

    with patch("app.core.config.settings", mock_settings):
        with patch("secrets.token_urlsafe", return_value="generated_pw") as mock_secrets:
            await init_db(mock_db)
            assert mock_secrets.called
            assert mock_db.add.called


@pytest.mark.asyncio
async def test_init_db_error_handles(mock_db):
    mock_db.execute.side_effect = Exception("DB Error")

    await init_db(mock_db)
    assert mock_db.rollback.called
