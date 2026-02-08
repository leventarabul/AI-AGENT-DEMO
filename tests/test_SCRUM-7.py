import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock
from agents.src.clients.demo_domain_client import create_event
from demo_domain.api_server import app

@pytest.fixture
def event_data():
    return {
        "name": "Test Event",
        "description": "This is a test event",
        "channel": "default"
    }

@pytest.mark.asyncio
async def test_create_event(event_data, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1}
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    response = await create_event(event_data)

    assert response == {"id": 1}

@pytest.mark.asyncio
async def test_create_event_with_channel(event_data, mocker):
    mock_create_event = mocker.patch("agents.src.clients.demo_domain_client.create_event")
    mock_create_event.return_value = {"id": 1}

    response = await app.post("/events/channel", json=event_data)

    assert response == {"id": 1}

@pytest.mark.asyncio
async def test_create_event_with_channel_default_channel(event_data, mocker):
    event_data.pop("channel")
    mock_create_event = mocker.patch("agents.src.clients.demo_domain_client.create_event")
    mock_create_event.return_value = {"id": 1}

    response = await app.post("/events/channel", json=event_data)

    assert response == {"id": 1}

@pytest.mark.asyncio
async def test_create_event_with_channel_error(event_data):
    response = await app.post("/events/channel", json={})

    assert response.status_code == 422