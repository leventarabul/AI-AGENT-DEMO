import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event_success(client):
    response = client.post("/events", json={"event_data": {"key": "value"}, "channel": "test"})
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_no_channel(client):
    response = client.post("/events", json={"event_data": {"key": "value"}})
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully"}

def test_create_event_error(client):
    with patch('main.logger.error') as mock_logger_error:
        response = client.post("/events", json={"event_data": {"key": "value"}, "channel": "test"})
        assert response.status_code == 200
        assert response.json() == {"message": "Error creating event"}
        mock_logger_error.assert_called_once()