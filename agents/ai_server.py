from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import os
from src.agents.event_agent import EventAgent
from src.agents.jira_agent import JiraAgent

app = FastAPI()

class AIEventRequest(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    base_amount: Optional[float] = 50.0
    event_data: Optional[Dict[str, Any]] = None

class JiraWebhookRequest(BaseModel):
    """Jira webhook payload (simplified)."""
    webhookEvent: str
    issue: Dict[str, Any]

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


async def _process_jira_task_in_background(issue_key: str):
    """Background task to process Jira issue with AI agent."""
    try:
        agent = JiraAgent(
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_token=os.getenv("JIRA_API_TOKEN"),
            ai_management_url=os.getenv("AI_MANAGEMENT_URL"),
            git_repo_path=os.getenv("GIT_REPO_PATH", "/tmp/repo"),
        )
        result = await agent.process_task(issue_key)
        print(f"✅ Jira task {issue_key} processed successfully:\n{result}")
    except Exception as e:
        print(f"❌ Error processing Jira task {issue_key}: {e}")


@app.post("/webhooks/jira")
async def jira_webhook(request: JiraWebhookRequest, background_tasks: BackgroundTasks):
    """
    Receive Jira webhook events.
    Filters for 'Development Waiting' status and dispatches to JiraAgent.
    """
    print(f"🔔 Jira webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in "Development Waiting" status
    if status == "Development Waiting":
        print(f"  Task ready: {issue_key} ({issue_type})")
        # Dispatch to background task
        background_tasks.add_task(_process_jira_task_in_background, issue_key)
        return {
            "status": "accepted",
            "issue_key": issue_key,
            "message": "Task dispatched to background processing"
        }
    else:
        return {
            "status": "skipped",
            "issue_key": issue_key,
            "status_current": status,
            "message": "Only 'Development Waiting' status is processed"
        }

