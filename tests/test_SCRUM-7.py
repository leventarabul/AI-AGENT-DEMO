import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app import app, Event

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "6789",
        "transaction_id": "54321",
        "merchant_id": "9876",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00",
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    data = response.json()
    assert "event_code" in data
    assert data["channel"] == "web"

def test_create_event_missing_channel(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "6789",
        "transaction_id": "54321",
        "merchant_id": "9876",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_invalid_channel(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "6789",
        "transaction_id": "54321",
        "merchant_id": "9876",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00",
        "channel": 123  # Invalid channel type
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422