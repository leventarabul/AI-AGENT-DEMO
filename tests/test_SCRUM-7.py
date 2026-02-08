import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_httpx_client():
    with patch("main.httpx.AsyncClient") as MockClient:
        yield MockClient

def test_create_event_success(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.return_value.json.return_value = {"id": 1, "name": "Event"}
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/events", json={"name": "Event"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Event"}

def test_create_event_http_error(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = httpx.HTTPStatusError(Mock(status_code=404))
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/events", json={"name": "Event"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_create_event_request_error(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = httpx.RequestError()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/events", json={"name": "Event"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Error connecting to demo-domain service"}

def test_trigger_event_processing_success(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.return_value.json.return_value = {"status": "Processing"}
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/admin/jobs/process-events")

    assert response.status_code == 200
    assert response.json() == {"status": "Processing"}

def test_trigger_event_processing_http_error(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = httpx.HTTPStatusError(Mock(status_code=403))
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/admin/jobs/process-events")

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}

def test_trigger_event_processing_request_error(client, mock_httpx_client):
    mock_client_instance = Mock()
    mock_client_instance.post.side_effect = httpx.RequestError()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post("/admin/jobs/process-events")

    assert response.status_code == 500
    assert response.json() == {"detail": "Error connecting to demo-domain service"}