from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from src.agents.event_agent import EventAgent

app = FastAPI()

class AIEventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    base_amount: Optional[float] = 50.0
    event_data: Optional[Dict[str, Any]] = None

@app.post("/ai-events")
async def ai_event(request: AIEventRequest):
    """
    Register event with AI-suggested reward
    
    - Event.amount = Transaction amount (what customer paid)
    - AI suggests reward amount based on customer history
    - Earnings created with AI suggestion
    """
    agent = EventAgent()
    try:
        # Use new method that properly separates transaction vs reward
        result = await agent.register_event_with_ai_reward(
            event_code=request.event_code,
            customer_id=request.customer_id,
            transaction_id=request.transaction_id,
            merchant_id=request.merchant_id,
            transaction_amount=request.base_amount,  # ← Müşterinin ödediği
            event_data=request.event_data
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
