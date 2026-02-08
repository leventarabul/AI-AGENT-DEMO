import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api_server import app, Event

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "54321",
        "merchant_id": "67890",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_missing_field(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "54321",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_invalid_channel(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "54321",
        "merchant_id": "67890",
        "amount": 100.0,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {},
        "channel": "invalid_channel"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422