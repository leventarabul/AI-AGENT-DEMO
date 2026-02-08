from typing import Optional
from fastapi import FastAPI

app = FastAPI()

@app.post("/events")
async def create_event():
    pass

@app.post("/admin/jobs/process-events")
async def trigger_event_processing_job():
    pass

@app.get("/events/{event_id}")
async def get_event_details(event_id: int):
    pass