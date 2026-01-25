from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
import asyncio
import os
from src.agents.event_agent import EventAgent
from src.agents.jira_agent import JiraAgent
from src.agents.code_review_agent import CodeReviewAgent
from src.agents.testing_agent import TestingAgent

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


async def _review_code_in_background(issue_key: str, code_files: List[Tuple[str, str]]):
    """Background task to review code with AI agent."""
    try:
        agent = CodeReviewAgent(
            ai_management_url=os.getenv("AI_MANAGEMENT_URL"),
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_token=os.getenv("JIRA_API_TOKEN"),
        )
        result = await agent.review_pull_request(issue_key, code_files)
        print(f"✅ Code review for {issue_key} completed:\n{result}")
    except Exception as e:
        print(f"❌ Error reviewing code for {issue_key}: {e}")


class CodeReviewWebhookRequest(BaseModel):
    """Code review webhook payload."""
    webhookEvent: str
    issue: Dict[str, Any]
    pull_request: Optional[Dict[str, Any]] = None
    code_files: List[Tuple[str, str]] = []  # [(filename, code), ...]


@app.post("/webhooks/code-review")
async def code_review_webhook(
    request: CodeReviewWebhookRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive code review webhook events.
    Filters for 'In Review' status, analyzes code, transitions to Testing or back to Development.
    """
    print(f"🔍 Code review webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in "In Review" status (PR ready for review)
    if status == "In Review" or status == "Code Ready":
        print(f"  Reviewing: {issue_key}")
        
        # If code_files not provided, extract from PR
        code_files = request.code_files or []
        
        # Dispatch to background task
        background_tasks.add_task(_review_code_in_background, issue_key, code_files)
        return {
            "status": "accepted",
            "issue_key": issue_key,
            "message": "Code review dispatched"
        }
    else:
        return {
            "status": "skipped",
            "issue_key": issue_key,
            "status_current": status,
            "message": "Only 'In Review' or 'Code Ready' status is processed"
        }

async def _run_tests_in_background(issue_key: str, test_files: List[str] = None):
    """Background task to run tests with TestingAgent."""
    try:
        agent = TestingAgent(
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_token=os.getenv("JIRA_API_TOKEN"),
            repo_path=os.getenv("GIT_REPO_PATH", "."),
        )
        result = await agent.run_tests(issue_key, test_files)
        print(f"✅ Testing for {issue_key} completed:\n{result}")
    except Exception as e:
        print(f"❌ Error running tests for {issue_key}: {e}")


class TestingWebhookRequest(BaseModel):
    """Testing webhook payload."""
    webhookEvent: str
    issue: Dict[str, Any]
    test_files: Optional[List[str]] = None


@app.post("/webhooks/testing")
async def testing_webhook(
    request: TestingWebhookRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive testing webhook events.
    Filters for 'Testing' status, runs tests, transitions to Done or back to Development.
    """
    print(f"🧪 Testing webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in "Testing" status
    if status == "Testing" or status == "Test Ready":
        print(f"  Running tests: {issue_key}")
        
        # Dispatch to background task
        background_tasks.add_task(_run_tests_in_background, issue_key, request.test_files)
        return {
            "status": "accepted",
            "issue_key": issue_key,
            "message": "Testing dispatched"
        }
    else:
        return {
            "status": "skipped",
            "issue_key": issue_key,
            "status_current": status,
            "message": "Only 'Testing' or 'Test Ready' status is processed"
        }