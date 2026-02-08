import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client():
    client = TestClient(app)
    return client

def test_create_event(client):
    data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "vwxyz",
        "amount": 100.00,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
    }
    response = client.post("/events", json=data, params={"channel": "web"})
    assert response.status_code == 200
    assert response.json()["channel"] == "web"

def test_create_event_missing_channel(client):
    data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "vwxyz",
        "amount": 100.00,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
    }
    response = client.post("/events", json=data)
    assert response.status_code == 422

def test_create_event_invalid_channel(client):
    data = {
        "event_code": "12345",
        "customer_id": "67890",
        "transaction_id": "abcde",
        "merchant_id": "vwxyz",
        "amount": 100.00,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": None,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
    }
    response = client.post("/events", json=data, params={"channel": 123})
    assert response.status_code == 422