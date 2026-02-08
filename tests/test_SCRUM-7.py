import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
from api_server import app, Event

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"id": 1, "status": "pending"}

def test_create_event_missing_required_fields(client):
    response = client.post("/events", json={})
    assert response.status_code == 422

def test_create_event_invalid_amount(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": "invalid",
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
    })
    assert response.status_code == 422

def test_create_event_invalid_date_format(client):
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "01-01-2022 00:00:00",
        "event_data": {"key": "value"},
    })
    assert response.status_code == 422

@patch('api_server.save_event_to_database')
def test_create_event_database_error(mock_save_event, client):
    mock_save_event.side_effect = Exception("Database error")
    response = client.post("/events", json={
        "event_code": "test_event",
        "customer_id": "123",
        "transaction_id": "456",
        "merchant_id": "789",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
    })
    assert response.status_code == 500