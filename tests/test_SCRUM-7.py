import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event_success(client):
    event_data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 50.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200

@patch('main.httpx.AsyncClient')
def test_create_event_api_error(mock_async_client, client):
    mock_async_client.return_value.post.side_effect = Exception("API error")
    event_data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 50.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 500

@patch('main.httpx.AsyncClient')
def test_create_event_connection_error(mock_async_client, client):
    mock_async_client.return_value.post.side_effect = httpx.RequestError("Connection error")
    event_data = {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 50.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 500