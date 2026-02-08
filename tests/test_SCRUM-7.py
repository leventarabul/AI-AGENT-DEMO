import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

def test_create_event_success(client):
    event_data = {"name": "Test Event"}
    response_mock = MagicMock()
    response_mock.json.return_value = {"id": 1}
    
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.post.return_value = response_mock
        response = client.post("/events", json=event_data)
    
    assert response.status_code == 200
    assert response.json() == {"event_id": 1, "status": "pending"}

def test_trigger_event_processing_success(client):
    response_mock = MagicMock()
    
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.post.return_value = response_mock
        response = client.post("/admin/jobs/process-events")
    
    assert response.status_code == 200
    assert response.json() == {"status": "triggered", "message": "Event processing job started"}

def test_get_event_details_success(client):
    event_id = 1
    response_mock = MagicMock()
    response_mock.json.return_value = {"id": event_id, "name": "Test Event"}
    
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.get.return_value = response_mock
        response = client.get(f"/events/{event_id}")
    
    assert response.status_code == 200
    assert response.json() == {"id": event_id, "name": "Test Event"}

def test_create_event_error(client):
    event_data = {"name": "Test Event"}
    
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.post.side_effect = Exception("Mocked error")
        response = client.post("/events", json=event_data)
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Error creating event"}

def test_trigger_event_processing_error(client):
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.post.side_effect = Exception("Mocked error")
        response = client.post("/admin/jobs/process-events")
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Error triggering event processing job"}

def test_get_event_details_error(client):
    event_id = 1
    
    with patch("main.httpx.AsyncClient") as AsyncClient:
        AsyncClient.return_value.get.side_effect = Exception("Mocked error")
        response = client.get(f"/events/{event_id}")
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Error getting event details"}