import pytest
import httpx

@pytest.fixture
def api_url():
    return "http://demo-domain-api:8000"

@pytest.fixture
def auth():
    return ("admin", "admin123")

@pytest.fixture
def event_data():
    return {
        "event_code": "purchase",
        "customer_id": "12345",
        "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
        "merchant_id": "67890",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "gender": "male"
    }

def test_create_event(api_url, auth, event_data):
    with httpx.Client(auth=auth) as client:
        response = client.post(f"{api_url}/events/", json=event_data)
    
    assert response.status_code == 200
    assert response.json()["event_code"] == event_data["event_code"]
    assert response.json()["customer_id"] == event_data["customer_id"]
    assert response.json()["transaction_id"] == event_data["transaction_id"]
    assert response.json()["merchant_id"] == event_data["merchant_id"]
    assert response.json()["amount"] == event_data["amount"]
    assert response.json()["transaction_date"] == event_data["transaction_date"]
    assert response.json()["gender"] == event_data["gender"]

def test_process_single_event(api_url, auth):
    with httpx.Client(auth=auth) as client:
        response = client.get(f"{api_url}/process_event")
    
    assert response.status_code == 200
    assert response.json()["success"] == True