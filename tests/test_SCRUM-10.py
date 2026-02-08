import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from agents.src.agents.SCRUM-10_impl import router

@pytest.fixture
def client():
    return TestClient(router)

def test_create_event_with_city(client):
    response = client.post("/events", json={"city": "Istanbul"})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

def test_create_event_without_city(client):
    response = client.post("/events")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

def test_process_events(client):
    response = client.post("/events/process")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

def test_get_event_details(client):
    event_id = 1

    with patch("agents.src.agents.SCRUM-10_impl.register_event") as mock_register_event:
        mock_register_event.return_value = event_id

        response = client.get(f"/events/{event_id}")
        assert response.status_code == 200
        assert response.json()["event_id"] == event_id
        assert response.json()["status"] == "processed"
        assert response.json()["matched_rule_id"] == 1

def test_failed_create_event(client):
    with patch("agents.src.agents.SCRUM-10_impl.register_event") as mock_register_event:
        mock_register_event.side_effect = Exception("Test exception")

        response = client.post("/events")
        assert response.status_code == 500

def test_failed_process_events(client):
    with patch("agents.src.agents.SCRUM-10_impl.trigger_event_processing") as \
    mock_trigger_event_processing:
        mock_trigger_event_processing.side_effect = Exception("Test exception")

        response = client.post("/events/process")
        assert response.status_code == 500

def test_failed_get_event_details(client):
    event_id = 1

    with patch("agents.src.agents.SCRUM-10_impl.register_event") as mock_register_event:
        mock_register_event.return_value = event_id

        with patch("agents.src.agents.SCRUM-10_impl.get_event_details") as mock_get_event_details:
            mock_get_event_details.side_effect = Exception("Test exception")

            response = client.get(f"/events/{event_id}")
            assert response.status_code == 404