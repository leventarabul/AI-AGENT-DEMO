import pytest
from httpx import HTTPStatusError, RequestError, TimeoutException
from unittest.mock import AsyncMock

@pytest.fixture
def mock_httpx_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_create_event_success(mock_httpx_client):
    mock_httpx_client.post.return_value.json.return_value = {"id": 1}
    
    event_data = {"name": "Test Event"}
    result = await create_event(event_data, client=mock_httpx_client)
    
    assert result == 1

@pytest.mark.asyncio
async def test_create_event_http_error(mock_httpx_client):
    mock_httpx_client.post.side_effect = HTTPStatusError(response=Mock(status_code=404))
    
    event_data = {"name": "Test Event"}
    result = await create_event(event_data, client=mock_httpx_client)
    
    assert result is None

@pytest.mark.asyncio
async def test_create_event_request_error(mock_httpx_client):
    mock_httpx_client.post.side_effect = RequestError()
    
    event_data = {"name": "Test Event"}
    result = await create_event(event_data, client=mock_httpx_client)
    
    assert result is None

@pytest.mark.asyncio
async def test_create_event_timeout_error(mock_httpx_client):
    mock_httpx_client.post.side_effect = TimeoutException()
    
    event_data = {"name": "Test Event"}
    result = await create_event(event_data, client=mock_httpx_client)
    
    assert result is None