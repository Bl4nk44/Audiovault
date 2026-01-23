from unittest.mock import patch

import pytest
from app.api.v1.system import check_for_updates


@pytest.mark.asyncio
async def test_check_update_semver_logic():
    """
    Verify that update check uses SemVer logic:
    - v2.0.0 > v1.9.9 (True)
    - v1.0.0 == v1.0.0 (False)
    - v1.0.0 < v1.0.1 (False) - This is the critical fix
    """

    # Test cases: (latest_remote, current_local, expected_update_available)
    cases = [
        ("v2.0.0", "v1.9.9", True),
        ("v1.0.0", "v1.0.0", False),
        ("v1.0.0", "v1.0.1", False),  # Local is newer
        ("v1.2.3", "1.2.3", False),  # v prefix handling
        ("v1.5.0", "1.4.9", True),
    ]

    # Manual mocks to avoid AsyncMock context manager issues
    class MockResponse:
        def __init__(self, data):
            self._data = data
            self.status = 200

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    class MockSession:
        def __init__(self, response):
            self.response = response

        def get(self, url):
            return self.response

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    for latest, current, expected in cases:
        # Mock settings
        with (
            patch("app.core.config.settings.ENVIRONMENT", "production"),
            patch("app.core.config.settings.VERSION", current),
        ):
            # Prepare response data
            data = {"tag_name": latest, "html_url": "http://github.com/release"}

            mock_resp = MockResponse(data)
            mock_sess = MockSession(mock_resp)

            # Patch ClientSession to return our manual session mock
            # When ClientSession() is called, it returns mock_sess
            with patch("aiohttp.ClientSession", return_value=mock_sess):
                result = await check_for_updates()

                if "error" in result:
                    pytest.fail(f"Function returned error: {result['error']}")

                assert result["update_available"] == expected, (
                    f"Failed for latest={latest}, current={current}. "
                    f"Expected {expected}, got {result['update_available']}"
                )
