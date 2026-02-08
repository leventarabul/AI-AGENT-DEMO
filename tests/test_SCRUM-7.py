import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    response = client.post("/events/", json={
        "event_code": "event_001",
        "customer_id": "customer_001",
        "transaction_id": "trans_001",
        "merchant_id": "merchant_001",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_missing_required_fields(client):
    response = client.post("/events/", json={})
    assert response.status_code == 422

@patch("main.save_event_to_database")
def test_create_event_database_error(mock_save_event, client):
    mock_save_event.side_effect = Exception("Database error")
    response = client.post("/events/", json={
        "event_code": "event_001",
        "customer_id": "customer_001",
        "transaction_id": "trans_001",
        "merchant_id": "merchant_001",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 500