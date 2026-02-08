import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
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
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"success": True}

@patch("app.httpx.AsyncClient")
def test_create_event_http_error(mock_async_client, client):
    mock_client = Mock()
    mock_client.post.side_effect = httpx.HTTPStatusError(response=Mock(status_code=400, json=lambda: {"error": "Bad Request"}))
    mock_async_client.return_value = mock_client

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
    response = client.post("/events", json=event_data)
    assert response.status_code == 400
    assert response.json() == {"error": "Bad Request"}

@patch("app.httpx.AsyncClient")
def test_create_event_request_error(mock_async_client, client):
    mock_client = Mock()
    mock_client.post.side_effect = httpx.RequestError("Connection Error")
    mock_async_client.return_value = mock_client

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
    response = client.post("/events", json=event_data)
    assert response.status_code == 500
    assert response.json() == {"detail": "Error making HTTP request"}