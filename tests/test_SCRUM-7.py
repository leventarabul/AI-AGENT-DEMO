import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.fixture
def test_app():
    from main import app
    return TestClient(app)

def test_create_event_success(test_app):
    response = test_app.post("/events", json={"channel": "test_channel"})
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel information"}

def test_create_event_missing_channel(test_app):
    response = test_app.post("/events", json={})
    assert response.status_code == 200
    assert response.json() == {"message": "Event created successfully with channel information"}

def test_create_event_error(test_app):
    with patch('main.logger.error') as mock_logger_error:
        response = test_app.post("/events", json={"channel": "test_channel"})
        assert response.status_code == 200
        assert response.json() == {"message": "Failed to create event with channel information"}
        mock_logger_error.assert_called_once()