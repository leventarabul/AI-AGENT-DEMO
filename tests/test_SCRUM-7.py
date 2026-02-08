import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    response = client.post("/events", json={"channel": "channel1"})
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel info"}

def test_create_event_no_channel(client):
    response = client.post("/events")
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel info"}

@patch("main.save_event")
def test_create_event_error(save_event_mock, client):
    save_event_mock.side_effect = Exception("Database error")
    response = client.post("/events", json={"channel": "channel1"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Error creating event"}