import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from httpx import HTTPStatusError

from main import app, Event, EventIn, HTTPException

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    session = Mock(spec=Session)
    return session

@pytest.fixture
def event_in():
    return EventIn(channel="test")

@pytest.fixture
def event():
    return Event(channel="test")

def test_create_event_success(mock_db_session, event_in, event):
    with patch('main.session', new=mock_db_session):
        response = client.post("/events/", json=event_in.dict())
        assert response.status_code == 200
        assert "id" in response.json()
        mock_db_session.add.assert_called_once_with(event)
        mock_db_session.commit.assert_called_once()

def test_create_event_db_error(mock_db_session, event_in):
    mock_db_session.add.side_effect = Exception("DB error")
    with patch('main.session', new=mock_db_session):
        with pytest.raises(HTTPStatusError) as e:
            client.post("/events/", json=event_in.dict())
        assert e.value.status_code == 500
        assert str(e.value) == "Failed to create event"
        mock_db_session.add.assert_called_once()
        mock_db_session.rollback.assert_called_once()
        mock_db_session.commit.assert_not_called()

def test_create_event_validation_error(event_in):
    event_in.channel = None
    with pytest.raises(HTTPStatusError) as e:
        client.post("/events/", json=event_in.dict())
    assert e.value.status_code == 422  # validation error status code