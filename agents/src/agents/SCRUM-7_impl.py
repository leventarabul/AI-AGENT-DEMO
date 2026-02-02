# Assuming that we are using SQLAlchemy for database operations
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String, index=True)
    # Other fields...

# Assuming that we use FastAPI for API operations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

app = FastAPI()

class EventIn(BaseModel):
    channel: str
    # Other fields...

@app.post("/events/")
async def create_event(event: EventIn):
    new_event = Event(**event.dict())
    try:
        session.add(new_event)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event")
    finally:
        session.close()
    return {"id": new_event.id}