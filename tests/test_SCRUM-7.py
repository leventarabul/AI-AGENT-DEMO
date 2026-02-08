import pytest
from fastapi.testclient import TestClient
from agents.SCRUM-7_impl import router, EventChannel

client = TestClient(router)

@pytest.fixture
def event_id():
    return 1

def test_add_event_channel_success(event_id):
    response = client.post(f"/events/{event_id}/channel", json={"channel": "test_channel"})
    assert response.status_code == 200
    assert response.json() == {"channel": "test_channel"}

def test_add_event_channel_missing_channel_field(event_id):
    response = client.post(f"/events/{event_id}/channel", json={})
    assert response.status_code == 422

def test_add_event_channel_invalid_event_id():
    response = client.post("/events/abc/channel", json={"channel": "test_channel"})
    assert response.status_code == 422

def test_add_event_channel_invalid_json_format(event_id):
    response = client.post(f"/events/{event_id}/channel", json="invalid_json")
    assert response.status_code == 422