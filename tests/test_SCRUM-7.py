# test_demo_domain_client.py

import pytest
from unittest.mock import AsyncMock
from httpx import Response
from clients.demo_domain_client import create_event

@pytest.fixture
def mock_httpx_client():
    client = AsyncMock()
    client.post.return_value = Response(status_code=200, json=lambda: {"id": 1})
    return client

@pytest.mark.asyncio
async def test_create_event_successful(mock_httpx_client):
    event_data = {"name": "Test Event"}
    result = await create_event(event_data)
    assert result == {"id": 1}

@pytest.mark.asyncio
async def test_create_event_http_error(mock_httpx_client):
    mock_httpx_client.post.return_value = Response(status_code=500)
    event_data = {"name": "Test Event"}
    with pytest.raises(Exception):
        await create_event(event_data)

@pytest.mark.asyncio
async def test_create_event_timeout_error(mock_httpx_client):
    mock_httpx_client.post.side_effect = TimeoutError
    event_data = {"name": "Test Event"}
    with pytest.raises(Exception):
        await create_event(event_data)