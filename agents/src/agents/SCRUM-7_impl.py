from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

DEMO_DOMAIN_URL = "http://demo-domain-api:8000"

@app.post("/events")
async def create_event(event_data: dict):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{DEMO_DOMAIN_URL}/events", json=event_data, auth=("admin", "admin123"))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json()["detail"])
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Error connecting to demo-domain service")

@app.post("/admin/jobs/process-events")
async def trigger_event_processing():
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{DEMO_DOMAIN_URL}/admin/jobs/process-events", auth=("admin", "admin123"))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json()["detail"])
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail="Error connecting to demo-domain service")