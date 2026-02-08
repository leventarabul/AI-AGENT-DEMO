import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event_success(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_missing_required_fields(client):
    response = client.post("/events", json={})
    assert response.status_code == 422

def test_create_event_internal_server_error(client):
    with patch('app.save_event_to_database') as mock_save_event:
        mock_save_event.side_effect = Exception()
        response = client.post("/events", json={
            "event_code": "test_event",
            "customer_id": "123",
            "transaction_id": "456",
            "merchant_id": "789",
            "amount": 100.0,
            "transaction_date": "2022-01-01",
            "event_data": {"key": "value"},
            "channel": "web"
        })
        assert response.status_code == 500