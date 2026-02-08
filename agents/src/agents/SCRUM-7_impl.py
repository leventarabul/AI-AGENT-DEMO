# agents/src/clients/demo_domain_client.py

import httpx
from typing import Optional

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def create_event(event_data: dict) -> Optional[int]:
    async with httpx.AsyncClient() as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        headers = {"Content-Type": "application/json"}
        try:
            response = await client.post(url, json=event_data, headers=headers)
            response.raise_for_status()
            event = response.json()
            return event.get("id")
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            print(f"HTTP error: {e}")
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            # Handle request errors
            print(f"Request error: {e}")
            return None

# Add any necessary error handling and logging