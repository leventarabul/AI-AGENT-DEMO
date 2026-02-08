# test_api_server.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api_server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    response = client.post("/events", json={"event_code": "12345", "customer_id": "67890", "transaction_id": "abcde", "merchant_id": "54321", "amount": 100.0, "transaction_date": "2022-01-01"})
    assert response.status_code == 200
    assert response.json() == {"status": "Event created successfully"}

@patch('database.save_event')
def test_create_event_db_save(mock_save_event, client):
    response = client.post("/events", json={"event_code": "12345", "customer_id": "67890", "transaction_id": "abcde", "merchant_id": "54321", "amount": 100.0, "transaction_date": "2022-01-01"})
    mock_save_event.assert_called_once()

def test_create_event_missing_required_fields(client):
    response = client.post("/events", json={"customer_id": "67890", "transaction_id": "abcde", "merchant_id": "54321", "amount": 100.0, "transaction_date": "2022-01-01"})
    assert response.status_code == 422

def test_create_event_invalid_amount(client):
    response = client.post("/events", json={"event_code": "12345", "customer_id": "67890", "transaction_id": "abcde", "merchant_id": "54321", "amount": "invalid", "transaction_date": "2022-01-01"})
    assert response.status_code == 422