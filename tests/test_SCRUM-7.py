import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from agents.src.clients.demo_domain_client import register_event, EventRequest
from demo_environment.api_server import app

@pytest.fixture
def event_data():
    return {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "channel": "web"
    }

@pytest.mark.asyncio
async def test_register_event(event_data):
    async with AsyncClient() as client:
        client.post = AsyncMock()
        await register_event(EventRequest(**event_data), "http://test-url", ("username", "password"))
        client.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_event(event_data):
    client = app.test_client
    response = await client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event registered successfully"}

@pytest.mark.asyncio
async def test_create_event_missing_data(event_data):
    del event_data["merchant_id"]
    client = app.test_client
    response = await client.post("/events", json=event_data)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_event_wrong_credentials(event_data):
    client = app.test_client
    response = await client.post("/events", json=event_data, headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == 401