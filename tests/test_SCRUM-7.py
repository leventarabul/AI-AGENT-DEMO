import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_httpx_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_update_event_channel(mock_httpx_client):
    event_id = 1
    channel = "test_channel"
    
    mock_httpx_client.patch.return_value.raise_for_status = AsyncMock()
    
    async with httpx.AsyncClient() as client:
        url = f"http://demo-domain-api:8000/events/{event_id}"
        payload = {"channel": channel}
        headers = {"Content-Type": "application/json"}
        
        await update_event_channel(event_id, channel)
        
        mock_httpx_client.patch.assert_awaited_once_with(url, json=payload, headers=headers)
        mock_httpx_client.patch.return_value.raise_for_status.assert_awaited_once()
        
@pytest.mark.asyncio
async def test_update_event_channel_error(mock_httpx_client):
    event_id = 1
    channel = "test_channel"
    
    mock_httpx_client.patch.side_effect = httpx.RequestError("Mocked error")
    
    with pytest.raises(httpx.RequestError):
        await update_event_channel(event_id, channel)