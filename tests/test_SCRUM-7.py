import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event_success(client):
    payload = {
        "event_code": "TEST",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_create_event_http_status_error(client):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(response=httpx.Response(500))
        payload = {
            "event_code": "TEST",
            "customer_id": "123",
            "transaction_id": "456",
            "merchant_id": "789",
            "amount": 100.0,
            "transaction_date": "2022-01-01",
            "event_data": {"key": "value"},
            "channel": "web"
        }
        response = await client.post("/events", json=payload)
        assert response.status_code == 500

@pytest.mark.asyncio
async def test_create_event_request_error(client):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.RequestError()
        payload = {
            "event_code": "TEST",
            "customer_id": "123",
            "transaction_id": "456",
            "merchant_id": "789",
            "amount": 100.0,
            "transaction_date": "2022-01-01",
            "event_data": {"key": "value"},
            "channel": "web"
        }
        response = await client.post("/events", json=payload)
        assert response.status_code == 500