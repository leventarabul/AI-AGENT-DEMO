import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_http_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_register_event_with_channel(mock_http_client):
    event_data = {"name": "test_event", "date": "2022-01-01"}
    channel = "test_channel"
    
    mock_http_client.post.return_value.json.return_value = {"status": "success"}
    
    result = await register_event_with_channel(event_data, channel)
    
    assert result == {"status": "success"}

@pytest.mark.asyncio
async def test_register_event_with_channel_edge_case(mock_http_client):
    event_data = {"name": "test_event"}
    channel = "test_channel"
    
    mock_http_client.post.return_value.json.return_value = {"status": "success"}
    
    result = await register_event_with_channel(event_data, channel)
    
    assert result == {"status": "success"}

@pytest.mark.asyncio
async def test_register_event_with_channel_error(mock_http_client):
    event_data = {"name": "test_event", "date": "2022-01-01"}
    channel = "test_channel"
    
    mock_http_client.post.side_effect = Exception("Error")
    
    with pytest.raises(Exception):
        await register_event_with_channel(event_data, channel)