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
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "channel": "online",
        "transaction_date": "2022-01-01",
        "event_data": {}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["event_code"] == "12345"

def test_create_event_missing_field(client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {}
    }
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

@patch("main.logging.error")
def test_create_event_exception(mock_logging, client):
    event_data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "54321",
        "amount": 100.0,
        "channel": "online",
        "transaction_date": "2022-01-01",
        "event_data": {}
    }
    with patch("main.save_event_to_database", side_effect=Exception("Database error")):
        response = client.post("/events", json=event_data)
        mock_logging.assert_called_once_with("Error creating event: Database error")
        assert response.status_code == 500