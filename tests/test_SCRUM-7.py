import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_event(client):
    response = client.post("/events")
    assert response.status_code == 200

def test_trigger_event_processing_job(client):
    response = client.post("/admin/jobs/process-events")
    assert response.status_code == 200

def test_get_event_details(client):
    event_id = 1
    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200