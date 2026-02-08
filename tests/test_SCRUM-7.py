import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock
from agents.clients.demo_domain_client import register_event_with_channel

@pytest.fixture
def mock_httpx_client():
    return MagicMock(AsyncClient)

@pytest.mark.asyncio
async def test_register_event_with_channel(mock_httpx_client):
    event_data = {"name": "Test Event"}
    channel = "test_channel"
    
    mock_httpx_client.post.return_value.json.return_value = {"id": 1}
    
    response = await register_event_with_channel(event_data, channel)
    
    assert response == {"id": 1}
    mock_httpx_client.post.assert_called_once_with("http://demo-domain-api:8000/events", json=event_data)
    mock_httpx_client.patch.assert_called_once_with("http://demo-domain-api:8000/events/1", json={"channel": channel})

@pytest.mark.asyncio
async def test_register_event_with_channel_error(mock_httpx_client):
    event_data = {"name": "Test Event"}
    channel = "test_channel"
    
    mock_httpx_client.post.side_effect = Exception("Error")
    
    with pytest.raises(Exception):
        await register_event_with_channel(event_data, channel)
        mock_httpx_client.patch.assert_not_called()