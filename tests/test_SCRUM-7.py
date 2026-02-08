import pytest
from unittest.mock import patch

@pytest.fixture
def mock_event():
    return Event(event_code='123', customer_id='456', transaction_id='789', merchant_id='987', amount=100.0, event_data='test_data', channel='online')

def test_create_event_success(client, mock_event):
    response = client.post("/events", json=mock_event.dict())
    assert response.status_code == 200
    assert response.json()["event_code"] == mock_event.event_code

def test_create_event_missing_channel(client, mock_event):
    del mock_event["channel"]
    response = client.post("/events", json=mock_event.dict())
    assert response.status_code == 422

def test_create_event_invalid_channel(client, mock_event):
    mock_event["channel"] = 123
    response = client.post("/events", json=mock_event.dict())
    assert response.status_code == 422

def test_create_event_database_error(client, mock_event):
    with patch('app.Event.create') as mock_create:
        mock_create.side_effect = Exception("Database error")
        response = client.post("/events", json=mock_event.dict())
        assert response.status_code == 500