import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime

from main import app, Event, create_event

@pytest.fixture
def test_client():
    return TestClient(app)

def test_create_event(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": datetime.now(),
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 200
    assert "id" in response.json()
    assert "status" in response.json()
    assert "created_at" in response.json()

def test_create_event_missing_data(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": datetime.now(),
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_invalid_amount(test_client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": "invalid",
        "event_data": {"key": "value"},
        "transaction_date": datetime.now(),
        "channel": "web"
    }
    response = test_client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_db_error(test_client, monkeypatch):
    mock_uuid = MagicMock(return_value="mock_id")
    monkeypatch.setattr("uuid.uuid4", mock_uuid)
    
    event_data = {
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "event_data": {"key": "value"},
        "transaction_date": datetime.now(),
        "channel": "web"
    }
    
    with pytest.raises(Exception):
        test_client.post("/events", json=event_data)