import pytest
from unittest.mock import patch
from my_module import EventLog, save_event_log

@pytest.fixture
def mock_event_id():
    return 1

@pytest.fixture
def mock_channel():
    return "test_channel"

def test_save_event_log_successful(mock_event_id, mock_channel):
    assert save_event_log(mock_event_id, mock_channel) is None

def test_event_log_creation():
    event_log = EventLog(channel="test_channel")
    assert event_log.channel == "test_channel"

def test_save_event_log_missing_channel(mock_event_id):
    with pytest.raises(TypeError):
        save_event_log(mock_event_id, None)

@patch('my_module.save_event_log', side_effect=Exception("Database Connection Error"))
def test_save_event_log_exception(mock_save_event_log, mock_event_id, mock_channel):
    with pytest.raises(Exception, match="Database Connection Error"):
        save_event_log(mock_event_id, mock_channel)