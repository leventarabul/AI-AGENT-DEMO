# demo-domain/tests/test_api_server.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
from api_server import app, save_event, Event

@pytest.fixture
def test_client():
    return TestClient(app)

def test_create_event_success(test_client):
    event_data = {
        "key1": "value1",
        "key2": "value2"
    }
    event = Event(event_code="test", customer_id="123", transaction_id="456", merchant_id="789", amount=100.0, transaction_date="2022-01-01", event_data=event_data, channel="web")
    
    response = test_client.post("/events", json=event.dict())
    
    assert response.status_code == 200
    assert response.json()["event_code"] == "test"
    assert response.json()["status"] == "pending"

@patch("api_server.save_event")
def test_create_event_error(mock_save_event, test_client):
    mock_save_event.side_effect = Exception("Database error")
    
    event = Event(event_code="test", customer_id="123", transaction_id="456", merchant_id="789", amount=100.0, transaction_date="2022-01-01", event_data={}, channel="web")
    
    response = test_client.post("/events", json=event.dict())
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Error creating event"

def test_save_event():
    event = save_event("test", "123", "456", "789", 100.0, "2022-01-01", {}, "web")
    
    assert event["event_code"] == "test"
    assert event["status"] == "pending"
    assert "created_at" in event
    assert "recorded_at" in event