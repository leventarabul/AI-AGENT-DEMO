import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event_successful(client):
    event_data = {
        "event_code": "TEST",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.json.return_value = {"message": "Event created successfully"}
        
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Event created successfully"}

@pytest.mark.asyncio
async def test_create_event_http_error(client):
    event_data = {
        "event_code": "TEST",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.raise_for_status.side_effect = \
        httpx.HTTPStatusError(response=httpx.Response(400))
        
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_event_request_error(client):
    event_data = {
        "event_code": "TEST",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.raise_for_status.side_effect = httpx.RequestError()
        
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 500