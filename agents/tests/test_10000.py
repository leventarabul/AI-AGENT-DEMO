import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from httpx import Response
from main import app, provision_code_handler, apply_campaign_rule

client = TestClient(app)

@pytest.fixture
def event():
    return {"provision_code": "test"}

@pytest.fixture
def no_code_event():
    return {"no_provision_code": "test"}

def test_provision_code_handler(event):
    with patch('main.apply_campaign_rule', return_value="test_code") as mock:
        result = asyncio.run(provision_code_handler(event))
        mock.assert_called_once_with('test')
        assert result == "test_code"

def test_provision_code_handler_no_provision_code(no_code_event):
    with pytest.raises(ValueError):
        asyncio.run(provision_code_handler(no_code_event))

@patch('main.AsyncClient')
def test_apply_campaign_rule(mock_client):
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = "test_rule"
    mock_client.get.return_value = mock_response

    result = asyncio.run(apply_campaign_rule("test_code"))
    mock_client.get.assert_called_once_with("http://campaignrule.api.com/test_code")
    assert result == "test_rule"

@patch('main.AsyncClient')
def test_apply_campaign_rule_failure(mock_client):
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    with pytest.raises(Exception):
        asyncio.run(apply_campaign_rule("test_code"))

def test_event_handler(event):
    with patch('main.provision_code_handler', return_value="test_code") as mock:
        response = client.post("/event/", json=event)
        assert response.status_code == 200
        assert response.json() == "test_code"
        mock.assert_called_once_with(event)

def test_event_handler_error(no_code_event):
    response = client.post("/event/", json=no_code_event)
    assert response.status_code == 200
    assert "error" in response.json()