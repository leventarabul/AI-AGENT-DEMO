import pytest
from httpx import Response
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from demo_environment.api_server import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_httpx_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_register_event_success(client, mock_httpx_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {"key": "value"}
    }
    mock_httpx_client.post.return_value = Response(status_code=200, json=lambda: {"status": "pending", "message": "Event registered successfully"})
    
    with patch("clients.demo_domain_client.httpx.AsyncClient", return_value=mock_httpx_client):
        response = await register_event(event_data)
    
    assert response == {"status": "pending", "message": "Event registered successfully"}

@pytest.mark.asyncio
async def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {"key": "value"}
    }
    response = client.post("/events", json=event_data)
    
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "message": "Event registered successfully"}

@pytest.mark.asyncio
async def test_create_event_missing_field(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00"  # missing event_data field
    }
    response = client.post("/events", json=event_data)
    
    assert response.status_code == 422
    assert response.json() == {"detail": [{"loc": ["body", "event_data"], "msg": "field required", "type": "value_error.missing"}]}