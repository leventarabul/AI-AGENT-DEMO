import pytest
import uuid
import requests

@pytest.fixture
def auth():
    return ('admin', 'admin123')

@pytest.fixture
def base_url():
    return 'http://demo-domain-api:8000'

def test_register_event(auth, base_url):
    event_data = {
        "event_code": "purchase",
        "customer_id": str(uuid.uuid4()),
        "transaction_id": str(uuid.uuid4()),
        "merchant_id": "12345",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "gender": "male"
    }
    
    response = requests.post(f"{base_url}/register_event", json=event_data, auth=auth)
    
    assert response.status_code == 200
    assert response.json()['event_code'] == event_data['event_code']

def test_process_single_event(auth, base_url):
    event_data = {
        "event_code": "purchase",
        "customer_id": str(uuid.uuid4()),
        "transaction_id": str(uuid.uuid4()),
        "merchant_id": "12345",
        "amount": 100.0,
        "transaction_date": "2022-01-01",
        "gender": "male"
    }
    
    response = requests.post(f"{base_url}/register_event", json=event_data, auth=auth)
    
    assert response.status_code == 200
    
    event_id = response.json()['id']
    
    event = requests.get(f"{base_url}/events/{event_id}", auth=auth).json()
    
    assert event['processed'] == False
    assert event['earnings'] == 0.0