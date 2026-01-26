"""Example: Integrating Jira Feedback with Webhook Handler

This example shows how to add Jira feedback to an existing webhook endpoint.
"""

import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any

from orchestrator.orchestrator import Orchestrator, Intent
from orchestrator.jira_feedback import post_trace_to_jira


app = FastAPI()
orchestrator = Orchestrator()


class JiraWebhookRequest(BaseModel):
    """Jira webhook payload."""
    webhookEvent: str
    issue: Dict[str, Any]


@app.post("/webhooks/jira")
async def jira_webhook(request: JiraWebhookRequest, background_tasks: BackgroundTasks):
    """
    Jira webhook handler with SDLC feedback loop.
    
    Flow:
    1. Receive Jira webhook
    2. Extract intent from issue
    3. Execute pipeline via orchestrator
    4. Post results back to Jira (in background)
    """
    
    # Extract issue details
    issue = request.issue
    issue_key = issue.get("key")
    issue_status = issue["fields"].get("status", {}).get("name")
    
    # Only process issues in "Development Waiting" status
    if issue_status != "Development Waiting":
        return {"status": "skipped", "reason": f"Issue not in Development Waiting (current: {issue_status})"}
    
    # Create intent from Jira issue
    intent = Intent(
        type="development_flow",  # Full SDLC: dev → review → test
        context={
            "issue_key": issue_key,
            "issue_summary": issue["fields"].get("summary"),
            "issue_description": issue["fields"].get("description"),
        },
        metadata={
            "source": "jira_webhook",
            "webhook_event": request.webhookEvent,
        },
    )
    
    # Execute pipeline (synchronous)
    result = orchestrator.execute(intent)
    
    # Post feedback to Jira (async, in background)
    if result.trace_id:
        background_tasks.add_task(
            post_trace_to_jira,
            trace_id=result.trace_id,
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
            update_status=True,  # Automatically transition issue based on result
        )
    
    return {
        "status": "ok",
        "trace_id": result.trace_id,
        "pipeline_status": result.status,
        "issue_key": issue_key,
    }


# Alternative: Immediate feedback (not recommended for webhooks)
@app.post("/api/execute")
async def execute_pipeline(intent_type: str, context: Dict[str, Any]):
    """
    Direct pipeline execution with immediate Jira feedback.
    
    Use this for API calls where you want to wait for feedback posting.
    For webhooks, prefer background tasks (see above).
    """
    
    intent = Intent(
        type=intent_type,
        context=context,
        metadata={"source": "api"},
    )
    
    # Execute pipeline
    result = orchestrator.execute(intent)
    
    # Post feedback immediately (await)
    if result.trace_id and context.get("issue_key"):
        await post_trace_to_jira(
            trace_id=result.trace_id,
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
            update_status=True,
        )
    
    return {
        "status": "ok",
        "trace_id": result.trace_id,
        "pipeline_status": result.status,
    }


# Environment Variables Required:
# - JIRA_URL: https://your-domain.atlassian.net
# - JIRA_USERNAME: your-email@example.com
# - JIRA_API_TOKEN: your-api-token (get from Atlassian account settings)
