# agents/src/clients/demo_domain_client.py

import httpx
from typing import Dict

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def register_event(event_data: Dict[str, str]) -> Dict[str, str]:
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        response = await client.post(url, json=event_data, auth=("admin", "admin123"))
        response.raise_for_status()
        return response.json()