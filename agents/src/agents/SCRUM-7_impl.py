from fastapi import FastAPI

app = FastAPI()

@app.post("/events")
async def create_event(event: dict):
    # Save event to the database including the channel field
    pass