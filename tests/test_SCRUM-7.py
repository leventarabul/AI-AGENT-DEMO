import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from agents.SCRUM-7_impl import router

client = TestClient(router)

@pytest.fixture
def valid_event_id():
    return 1

@pytest.fixture
def invalid_event_id():
    return 0

def test_add_channel_valid_event_id(valid_event_id):
    response = client.post("/events/1/channel", json={"channel": "test_channel"})
    assert response.status_code == 200
    assert response.json() == {"event_id": valid_event_id, "channel": "test_channel"}

def test_add_channel_invalid_event_id(invalid_event_id):
    response = client.post(f"/events/{invalid_event_id}/channel", json={"channel": "test_channel"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}

@patch('agents.SCRUM-7_impl.router.add_channel')
def test_add_channel_mocked_update_event(mock_add_channel):
    mock_add_channel.return_value = {"event_id": 1, "channel": "mocked_channel"}
    response = client.post("/events/1/channel", json={"channel": "test_channel"})
    assert response.status_code == 200
    assert response.json() == {"event_id": 1, "channel": "mocked_channel"}