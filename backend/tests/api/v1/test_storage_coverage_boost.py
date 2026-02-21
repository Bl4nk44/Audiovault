"""
Coverage boost for V1 Storage API.
Targets: storage stats and summary.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_storage_stats(client: AsyncClient, admin_token_headers):
    response = await client.get("/api/v1/storage/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "disk_total_bytes" in data
    assert "disk_free_bytes" in data


@pytest.mark.asyncio
async def test_get_storage_summary(client: AsyncClient, admin_token_headers):
    response = await client.get("/api/v1/storage/summary", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "completed" in data
    assert "total" in data
