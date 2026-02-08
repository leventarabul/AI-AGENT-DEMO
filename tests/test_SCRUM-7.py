import pytest
from httpx import Response
from unittest.mock import AsyncMock, patch
from agents.src.clients.demo_domain_client import register_event, DEMO_DOMAIN_URL

@pytest.fixture
def event_data():
    return {
        "name": "Test Event",
        "date": "2022-01-01",
        "location": "Test Location"
    }

@pytest.mark.asyncio
async def test_register_event_success(event_data):
    expected_response = {"status": "success"}
    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_client = MockAsyncClient.return_value
        mock_client.post.return_value = Response(200, json=expected_response)
        
        response = await register_event(event_data)
        
        assert response == expected_response
        mock_client.post.assert_called_once_with(f"{DEMO_DOMAIN_URL}/events", json=event_data, auth=("admin", "admin123"))

@pytest.mark.asyncio
async def test_register_event_error(event_data):
    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_client = MockAsyncClient.return_value
        mock_client.post.return_value = Response(400)
        
        with pytest.raises(Exception):
            await register_event(event_data)
        
        mock_client.post.assert_called_once_with(f"{DEMO_DOMAIN_URL}/events", json=event_data, auth=("admin", "admin123"))