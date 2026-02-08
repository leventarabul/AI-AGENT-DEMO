import pytest
from httpx import AsyncClient
from unittest.mock import patch
from agents.src.clients.demo_domain_client import register_event

@pytest.fixture
def event_data():
    return {"name": "Test Event", "date": "2022-01-01"}

@pytest.mark.asyncio
async def test_register_event_success(event_data):
    with patch('agents.src.clients.demo_domain_client.httpx.AsyncClient') as mock_client:
        mock_response = {"status": "success"}
        mock_client.return_value.post.return_value = mock_response

        response = await register_event(event_data)

        assert response == mock_response

@pytest.mark.asyncio
async def test_register_event_error(event_data):
    with patch('agents.src.clients.demo_domain_client.httpx.AsyncClient') as mock_client:
        mock_client.return_value.post.side_effect = Exception("Connection error")

        with pytest.raises(Exception):
            await register_event(event_data)