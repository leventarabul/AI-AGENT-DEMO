# test_api_server.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api_server import app

@pytest.fixture
def client():
    client = TestClient(app)
    yield client

def test_create_event_success(client):
    event_data = {
        "event_code": "1234",
        "customer_id": "5678",
        "transaction_id": "91011",
        "merchant_id": "1213",
        "amount": 100.0,
        "transaction_date": "2023-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert "message" in response.json()
    assert "suggestion" in response.json()

@patch('api_server.httpx.AsyncClient.post')
def test_create_event_with_mocked_response(mock_post, client):
    mock_post.return_value.json.return_value = {"suggestion": "Mocked suggestion"}
    event_data = {
        "event_code": "1234",
        "customer_id": "5678",
        "transaction_id": "91011",
        "merchant_id": "1213",
        "amount": 100.0,
        "transaction_date": "2023-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["suggestion"] == "Mocked suggestion"

def test_create_event_missing_data(client):
    event_data = {
        "event_code": "1234",
        "customer_id": "5678",
        "transaction_id": "91011",
        "merchant_id": "1213",
        "amount": 100.0,
        "transaction_date": "2023-01-01T00:00:00",
        "event_data": {"key": "value"}
        # Missing "channel" key
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_invalid_data(client):
    event_data = {
        "event_code": "1234",
        "customer_id": "5678",
        "transaction_id": "91011",
        "merchant_id": "1213",
        "amount": "invalid_amount",  # Invalid amount type
        "transaction_date": "2023-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422