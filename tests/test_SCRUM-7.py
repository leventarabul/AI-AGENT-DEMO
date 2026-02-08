import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event(client):
    event_data = {"name": "Test Event"}
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=200, json=lambda: {"id": 1})
        response = client.post("/events", json=event_data)
        assert response.status_code == 200
        assert response.json() == {"id": 1}

def test_process_event(client):
    event_id = 1
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=200, json=lambda: {"id": event_id, "status": "processed"})
        response = client.post(f"/events/{event_id}/process")
        assert response.status_code == 200
        assert response.json() == {"id": event_id, "status": "processed"}

def test_generate_suggestion(client):
    prompt = "Test prompt"
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=200, json=lambda: {"suggestion": "Test suggestion"})
        response = client.post("/ai/generate", json={"prompt": prompt})
        assert response.status_code == 200
        assert response.json() == {"suggestion": "Test suggestion"}

def test_create_event_error(client):
    event_data = {"name": "Test Event"}
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=400, json=lambda: {"detail": "Bad Request"})
        response = client.post("/events", json=event_data)
        assert response.status_code == 400
        assert response.json() == {"detail": "Bad Request"}

def test_process_event_error(client):
    event_id = 1
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=500, json=lambda: {"detail": "Internal Server Error"})
        response = client.post(f"/events/{event_id}/process")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}

def test_generate_suggestion_error(client):
    prompt = "Test prompt"
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=404, json=lambda: {"detail": "Not Found"})
        response = client.post("/ai/generate", json={"prompt": prompt})
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}