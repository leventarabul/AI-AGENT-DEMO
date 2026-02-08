import pytest
from httpx import Response
from unittest.mock import AsyncMock

@pytest.fixture
def mock_httpx_client():
    with patch('httpx.AsyncClient') as MockClient:
        yield MockClient.return_value

@pytest.mark.asyncio
async def test_register_event(mock_httpx_client):
    event_data = {"name": "Test Event"}
    expected_response = {"status": "success"}
    
    mock_httpx_client.post.return_value = Response(200, json=expected_response)
    
    response = await register_event(event_data)
    
    assert response == expected_response

@pytest.mark.asyncio
async def test_load_context():
    channel = "test_channel"
    expected_context = {"channel": channel}
    
    context = await load_context(channel)
    
    assert context == expected_context