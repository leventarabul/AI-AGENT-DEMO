import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_receive_event_channel_success(client):
    response = client.post("/event/channel", json={"channel": "test_channel"})
    assert response.status_code == 200
    assert response.json() == {"message": "Event channel information received successfully"}

def test_receive_event_channel_error(client):
    response = client.post("/event/channel", json={"channel": ""})
    assert response.status_code == 200
    assert response.json() == {"message": "Error processing event channel"}

@patch('main.logger')
def test_receive_event_channel_log_info(mock_logger, client):
    response = client.post("/event/channel", json={"channel": "test_channel"})
    assert response.status_code == 200
    mock_logger.info.assert_called_with("Received event channel: test_channel")

@patch('main.logger')
def test_receive_event_channel_log_error(mock_logger, client):
    response = client.post("/event/channel", json={"channel": ""})
    assert response.status_code == 200
    mock_logger.error.assert_called()