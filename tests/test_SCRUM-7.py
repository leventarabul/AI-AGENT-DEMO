# demo-domain/tests/test_api_server.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api_server import app

@pytest.fixture
def client():
    client = TestClient(app)
    return client

def test_create_event_success(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "message": "Event created successfully"}

@patch('api_server.httpx.AsyncClient')
def test_create_event_error(mock_client, client):
    mock_client.return_value.post.side_effect = Exception("Mocked error")
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}

@patch('api_server.httpx.AsyncClient')
def test_create_event_http_error(mock_client, client):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Mocked HTTP error")
    mock_client.return_value.post.return_value = mock_response
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 500
    assert response.json() == {"detail": "Error calling ai-management service"}

def test_create_event_missing_field(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"}
    })
    assert response.status_code == 422