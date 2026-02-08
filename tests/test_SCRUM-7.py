import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_create_event_with_channel_info(client):
    response = client.post("/events", json={
        "id": 1,
        "event_code": "ABC123",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "MERCHANT",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
        "processed_at": None,
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel information"}

def test_create_event_missing_channel_info(client):
    response = client.post("/events", json={
        "id": 1,
        "event_code": "ABC123",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "MERCHANT",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
        "processed_at": None
    })
    assert response.status_code == 422

@patch("routers.events.create_event")
def test_create_event_mocked_function(mock_create_event, client):
    mock_create_event.return_value = {"message": "Mocked Event created successfully with channel information"}
    response = client.post("/events", json={
        "id": 1,
        "event_code": "ABC123",
        "customer_id": "12345",
        "transaction_id": "67890",
        "merchant_id": "MERCHANT",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
        "processed_at": None,
        "channel": "web"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Mocked Event created successfully with channel information"}