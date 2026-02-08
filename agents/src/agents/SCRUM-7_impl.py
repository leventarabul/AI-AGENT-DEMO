# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def create_event(event_data: dict) -> dict:
    url = f"{DEMO_DOMAIN_URL}/events"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=event_data, auth=("admin", "admin123"))
        resp.raise_for_status()
        return resp.json()