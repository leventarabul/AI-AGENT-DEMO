import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    
    with patch("main.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post = AsyncMock(return_value=MockResponse(status_code=200, json_data={"success": True}))
        response = await client.post("/events", json=event_data)
        assert response.status_code == 200
        assert response.json() == {"success": True}

@pytest.mark.asyncio
async def test_create_event_http_error(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    
    with patch("main.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post = AsyncMock(return_value=MockResponse(status_code=400, json_data={"detail": "Bad Request"}))
        response = await client.post("/events", json=event_data)
        assert response.status_code == 400
        assert response.json() == {"detail": "Bad Request"}

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    async def json(self):
        return self.json_data