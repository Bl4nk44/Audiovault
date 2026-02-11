from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_logs(client: AsyncClient):
    # Mock log file content
    with patch("app.api.v1.system._get_log_file_path") as mock_path:
        mock_path.return_value = Path("/tmp/audiovault.log")
        with patch("app.api.v1.system._read_last_lines", return_value=["line1", "line2"]):
            response = await client.get("/api/v1/system/logs?lines=2")
            assert response.status_code == 200
            assert response.json() == ["line1", "line2"]


@pytest.mark.asyncio
async def test_system_stats(client: AsyncClient):
    with patch("psutil.cpu_percent", return_value=10.0):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.total = 1000
            mock_mem.return_value.used = 500
            mock_mem.return_value.percent = 50.0
            with patch("psutil.disk_usage") as mock_disk:
                mock_disk.return_value.total = 2000
                mock_disk.return_value.used = 1000
                mock_disk.return_value.percent = 50.0
                with patch("psutil.net_io_counters") as mock_net:
                    mock_net.return_value.bytes_sent = 100
                    mock_net.return_value.bytes_recv = 200

                    response = await client.get("/api/v1/system/stats")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["cpu"]["percent"] == pytest.approx(10.0)
                    assert data["memory"]["total"] == 1000


@pytest.mark.asyncio
async def test_check_update_production(client: AsyncClient):
    mock_settings = MagicMock()
    mock_settings.ENVIRONMENT = "production"
    mock_settings.VERSION = "v1.0.0"

    # Mock aiohttp response
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"tag_name": "v1.1.0", "html_url": "http://github/release"}

    # This is internal helper test
    from app.api.v1.system import _check_production_update

    with patch("aiohttp.ClientSession.get", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))):
        res = await _check_production_update(mock_settings)
        assert res["update_available"] is True
        assert res["latest_version"] == "1.1.0"


@pytest.mark.asyncio
async def test_check_update_development(client: AsyncClient):
    with patch("app.api.v1.system.Path.exists", return_value=True):
        with patch("app.api.v1.system.Path.read_text", return_value="local_sha"):
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = {"sha": "remote_sha", "html_url": "http://github/commit"}

            from app.api.v1.system import _check_development_update

            with patch(
                "aiohttp.ClientSession.get", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
            ):
                res = await _check_development_update()
                assert res["update_available"] is True
                assert res["current_version"] == "local_s"  # slice [:7]
