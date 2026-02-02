import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app import app, Event, EventRequest

@pytest.fixture
def test_client():
    client = TestClient(app)
    yield client

def test_create_event_success(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00Z",
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["event_code"] == event_data["event_code"]

def test_create_event_missing_field(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00Z"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 422

@patch('app.Event.save', MagicMock())
def test_create_event_database_error(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": "2022-01-01T00:00:00Z",
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 500