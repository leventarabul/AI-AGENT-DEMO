import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_httpx_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_register_event_successful(mock_httpx_client):
    mock_httpx_client.post.return_value = AsyncMock(status_code=200)
    
    await register_event("test_channel", {"key": "value"})
    
    mock_httpx_client.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_event_successful():
    event_data = {"key": "value"}
    response = await client.post("/events", json={"channel": "test_channel", "event_data": event_data})
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_create_event_invalid_data():
    response = await client.post("/events", json={"channel": "test_channel"})
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_event_error():
    response = await client.post("/events", json={"channel": "test_channel", "event_data": {}})
    
    assert response.status_code == 500