import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response_data = {"status": "success"}

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.json.return_value = response_data

        response = await client.post("/events", json=event_data)

    assert response.status_code == 200
    assert response.json() == response_data

@pytest.mark.asyncio
async def test_create_event_http_error(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.raise_for_status.side_effect = \
        httpx.HTTPStatusError(response=Mock(status_code=404))

        response = await client.post("/events", json=event_data)

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_event_request_error(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
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