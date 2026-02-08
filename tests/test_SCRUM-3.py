import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app import app, Event

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    data = response.json()
    assert "event_id" in data
    assert "reward" in data

@pytest.mark.asyncio
async def test_create_event_ai_service_error(client):
    with patch("app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post = \
        AsyncMock(side_effect=httpx.HTTPStatusError(response=Mock(status_code=400)))
        event_data = {
            "event_code": "test_event",
            "customer_id": "12345",
            "transaction_id": "67890",
            "merchant_id": "54321",
            "amount": 100.0,
            "transaction_date": "2022-01-01",
            "event_data": {"key": "value"}
        }
        response = client.post("/events", json=event_data)
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_event_demo_domain_error(client):
    with patch("app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.post = AsyncMock()
        mock_client.return_value.post.side_effect = [AsyncMock(), \
        AsyncMock(side_effect=httpx.HTTPStatusError(response=Mock(status_code=500))]

        event_data = {
            "event_code": "test_event",
            "customer_id": "12345",
            "transaction_id": "67890",
            "merchant_id": "54321",
            "amount": 100.0,
            "transaction_date": "2022-01-01",
            "event_data": {"key": "value"}
        }
        response = client.post("/events", json=event_data)
        assert response.status_code == 500