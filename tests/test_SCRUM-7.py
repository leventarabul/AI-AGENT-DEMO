import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=AsyncClient)

@pytest.mark.asyncio
async def test_create_event_success(mock_http_client):
    mock_http_client.post.return_value = {"channel": "test_channel", "event_data": {"key": "value"}}
    
    response = await create_event("test_channel", {"key": "value"}, mock_http_client)
    
    assert response == {"channel": "test_channel", "event_data": {"key": "value"}}

@pytest.mark.asyncio
async def test_create_event_invalid_response(mock_http_client):
    mock_http_client.post.return_value = {"status_code": 400, "reason": "Bad Request"}
    
    with pytest.raises(Exception):
        await create_event("test_channel", {"key": "value"}, mock_http_client)

@pytest.mark.asyncio
async def test_create_event_connection_error(mock_http_client):
    mock_http_client.post.side_effect = ConnectionError
    
    with pytest.raises(ConnectionError):
        await create_event("test_channel", {"key": "value"}, mock_http_client)

@pytest.mark.asyncio
async def test_create_event_timeout(mock_http_client):
    mock_http_client.post.side_effect = TimeoutError
    
    with pytest.raises(TimeoutError):
        await create_event("test_channel", {"key": "value"}, mock_http_client)