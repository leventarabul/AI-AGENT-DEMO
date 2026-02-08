import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_event():
    return Event(
        event_code="123",
        customer_id="456",
        transaction_id="789",
        merchant_id="987",
        amount=100.0,
        transaction_date=datetime.now(),
        event_data={"key": "value"},
        channel="web"
    )

def test_create_event_endpoint_success(client, mock_event):
    response = client.post("/events", json=mock_event.dict())
    assert response.status_code == 200

def test_save_event_to_db_success(mock_event):
    mock_execute = MagicMock()
    database.execute = mock_execute

    save_event_to_db(mock_event)

    mock_execute.assert_called_once()

def test_create_event_endpoint_missing_channel(client, mock_event):
    del mock_event.channel
    response = client.post("/events", json=mock_event.dict())
    assert response.status_code == 422

def test_save_event_to_db_missing_channel(mock_event):
    del mock_event.channel
    with pytest.raises(Exception):
        save_event_to_db(mock_event)

def test_create_event_endpoint_invalid_data(client):
    response = client.post("/events", json={"invalid": "data"})
    assert response.status_code == 422

def test_save_event_to_db_invalid_data():
    with pytest.raises(Exception):
        save_event_to_db(Event())