import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.fixture
def event_data():
    return {
        "event_code": "123",
        "customer_id": "456",
        "transaction_id": "789",
        "merchant_id": "101112",
        "amount": 100.0,
        "transaction_date": "2022-01-01T00:00:00",
        "event_data": {"key": "value"},
        "status": "success",
        "matched_rule_id": 1,
        "error_message": None,
        "created_at": "2022-01-01T00:00:00",
        "recorded_at": "2022-01-01T00:00:00",
        "processed_at": None,
        "channel": "web"
    }

def test_create_event_success(client: TestClient, event_data):
    response = client.post("/events", json=event_data)
    assert response.status_code == 200
    assert response.json()["event_code"] == event_data["event_code"]

def test_create_event_missing_channel(client: TestClient, event_data):
    del event_data["channel"]
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

def test_create_event_invalid_channel(client: TestClient, event_data):
    event_data["channel"] = 123
    response = client.post("/events", json=event_data)
    assert response.status_code == 422

@patch("app.execute_insert_query")
def test_create_event_insert_query(mock_execute_insert_query, client: TestClient, event_data):
    client.post("/events", json=event_data)
    mock_execute_insert_query.assert_called_once()