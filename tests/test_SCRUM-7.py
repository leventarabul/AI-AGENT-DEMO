import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event(client):
    response = client.post("/events", json={"name": "event1", "channel": "channel1"})
    assert response.status_code == 200

def test_create_event_missing_channel(client):
    response = client.post("/events", json={"name": "event1"})
    assert response.status_code == 422

def test_create_event_invalid_data(client):
    response = client.post("/events", json={"name": "event1", "channel": 123})
    assert response.status_code == 422

@patch('main.save_event_to_database')
def test_create_event_database(mock_save_event, client):
    response = client.post("/events", json={"name": "event1", "channel": "channel1"})
    assert response.status_code == 200
    mock_save_event.assert_called_once()