import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.50,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_missing_field(client):
    event_data = {
        "event_code": "test_event",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "54321",
        "amount": 100.50,
        "transaction_date": "2022-01-01T12:00:00",
        "event_data": {"key": "value"}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_database_error(client):
    with patch('main.Database.insert_event', side_effect=Exception("Database error")):
        event_data = {
            "event_code": "test_event",
            "customer_id": "12345",
            "transaction_id": "67890",
            "merchant_id": "54321",
            "amount": 100.50,
            "transaction_date": "2022-01-01T12:00:00",
            "event_data": {"key": "value"},
            "channel": "web"
        }
        response = client.post("/events", json=event_data)
        assert response.status_code == 500