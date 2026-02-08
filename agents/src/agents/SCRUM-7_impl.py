# agents/src/clients/demo_domain_client.py

import httpx

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

async def create_event(event_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{DEMO_DOMAIN_URL}/events"
        response = await client.post(url, json=event_data, auth=("admin", "admin123"))
        response.raise_for_status()
        return response.json()

# demo-domain/src/demo-environment/api_server.py

from fastapi import FastAPI

app = FastAPI()

@app.post("/events/channel")
async def create_event_with_channel(event_data: dict) -> dict:
    event_data["channel"] = event_data.get("channel", "default")
    return await create_event(event_data)