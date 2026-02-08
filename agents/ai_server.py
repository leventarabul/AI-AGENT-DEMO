from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
import asyncio
import os
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from agents directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
from src.agents.event_agent import EventAgent
from src.agents.jira_agent import JiraAgent
from src.agents.code_review_agent import CodeReviewAgent
from src.agents.testing_agent import TestingAgent
from src.middleware.webhook_middleware import verify_jira_webhook_signature
from src.scheduler import get_scheduler

logger = logging.getLogger(__name__)

# Startup/shutdown events for scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage scheduler lifecycle."""
    # Startup
    scheduler_enabled = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"
    scheduler = None
    if scheduler_enabled:
        scheduler = get_scheduler()
        scheduler.start()
        logger.info("Scheduler enabled")
    else:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false)")
    yield
    # Shutdown
    if scheduler:
        scheduler.stop()

app = FastAPI(lifespan=lifespan)

# Add webhook signature verification middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=verify_jira_webhook_signature)

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
    logger.info(f"\n🚀 [BACKGROUND] Starting task processing for {issue_key}")
    try:
        agent = JiraAgent(
            jira_url=os.getenv("JIRA_URL"),
            jira_username=os.getenv("JIRA_USERNAME"),
            jira_token=os.getenv("JIRA_API_TOKEN"),
            ai_management_url=os.getenv("AI_MANAGEMENT_URL"),
            git_repo_path=os.getenv("GIT_REPO_PATH", "/tmp/repo"),
        )
        result = await agent.process_task(issue_key)
        logger.info(f"✅ [BACKGROUND] Jira task {issue_key} processed successfully:\n{result}")
    except Exception as e:
        logger.info(f"❌ [BACKGROUND] Error processing Jira task {issue_key}: {e}")
        import traceback
        traceback.print_exc()


@app.post("/webhooks/jira")
async def jira_webhook(request: JiraWebhookRequest, background_tasks: BackgroundTasks):
    """
    Receive Jira webhook events.
    Filters for 'Development Waiting' status and dispatches to JiraAgent.
    """
    logger.info(f"🔔 Jira webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in "Waiting Development" status
    if status == "Waiting Development":
        logger.info(f"  Task ready: {issue_key} ({issue_type})")
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
        logger.info(f"📋 Starting code review for {issue_key}")
        repo_root = os.getenv("GIT_REPO_PATH", "/app")
        agent = CodeReviewAgent(repo_root=repo_root)

        if not code_files:
            code_files = _collect_code_files_from_repo(repo_root)

        result = await agent.review_pull_request(issue_key, code_files)
        logger.info(f"✅ Code review for {issue_key} completed:\n{result}")

        await _post_review_result_to_jira(issue_key, result)
    except Exception as e:
        logger.error(f"❌ Error reviewing code for {issue_key}: {e}", exc_info=True)


def _collect_code_files_from_repo(repo_root: str) -> List[Tuple[str, str]]:
    """Collect changed files from git for review.

    Returns a list of (file_path, content) tuples.
    """
    if not os.path.exists(os.path.join(repo_root, ".git")):
        logger.warning(f"Repo not found at {repo_root}; skipping git diff")
        return []

    def _run_git(args: List[str]) -> str:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
            },
        )
        return result.stdout.strip()

    def _ref_exists(ref: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
            },
        )
        return result.returncode == 0

    base_ref = None
    for ref in ["origin/main", "origin/master", "main", "master"]:
        if _ref_exists(ref):
            base_ref = ref
            break

    changed_files: List[str] = []
    if base_ref:
        diff_output = _run_git(["diff", "--name-only", f"{base_ref}...HEAD"])
        if diff_output:
            changed_files = [line.strip() for line in diff_output.splitlines() if line.strip()]

    if not changed_files:
        show_output = _run_git(["show", "--name-only", "--pretty=", "HEAD"])
        if show_output:
            changed_files = [line.strip() for line in show_output.splitlines() if line.strip()]

    code_files: List[Tuple[str, str]] = []
    for rel_path in changed_files:
        abs_path = os.path.join(repo_root, rel_path)
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            code_files.append((rel_path, content))
        except UnicodeDecodeError:
            continue

    return code_files


async def _post_review_result_to_jira(issue_key: str, review_result: Any) -> None:
    """Post review result to Jira and transition status."""
    jira_url = os.getenv("JIRA_URL")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not jira_url or not jira_username or not jira_token:
        logger.warning("Jira credentials missing; skipping status update")
        return

    from src.clients.jira_client import JiraClient
    from src.agents.code_review_agent import ReviewDecision, format_review_comment

    jira_client = JiraClient(
        jira_url=jira_url,
        username=jira_username,
        api_token=jira_token,
    )

    decision = getattr(review_result, "decision", None)
    reasoning = getattr(review_result, "reasoning", "")

    if decision == ReviewDecision.APPROVE:
        comment = "✅ " + format_review_comment(review_result)
        target_names = ["Testing", "Test Ready", "Ready for Testing"]
    elif decision == ReviewDecision.REQUEST_CHANGES:
        comment = "⚠️ " + format_review_comment(review_result)
        target_names = ["Waiting Development", "In Development", "To Do"]
    else:
        comment = "🚫 " + format_review_comment(review_result)
        target_names = ["Waiting Development", "In Development", "To Do", "Blocked"]

    await jira_client.add_comment(issue_key, comment)
    await _transition_issue_to_status(jira_client, issue_key, target_names)


async def _transition_issue_to_status(
    jira_client: Any,
    issue_key: str,
    target_names: List[str],
) -> None:
    """Transition Jira issue to first matching status name."""
    try:
        transitions = await jira_client.get_transitions(issue_key)
        target = None
        for name in target_names:
            for t in transitions:
                if t.get("name") == name:
                    target = t
                    break
            if target:
                break
        if not target:
            logger.warning(
                "No matching transition found for %s; skipping status change",
                target_names,
            )
            return
        await jira_client.transition_issue(issue_key, transition_id=target.get("id"))
        logger.info(f"Transitioned '{issue_key}' to '{target.get('name')}'")
    except Exception as e:
        logger.warning(f"Transition error for {issue_key}: {e}")


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
    logger.info(f"🔍 Code review webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in review-ready status (PR ready for review)
    if status in ("In Review", "Code Review", "Code Ready"):
        logger.info(f"  Reviewing: {issue_key}")
        
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
        from src.agents.testing_agent import TestStatus
        from src.clients.jira_client import JiraClient

        repo_root = os.getenv("GIT_REPO_PATH", ".")
        agent = TestingAgent(repo_root=repo_root)
        result = agent.execute(
            {
                "qa_mode": True,
                "issue_key": issue_key,
                "test_files": test_files,
                "test_path": "tests/",
            }
        )
        logger.info(f"✅ Testing for {issue_key} completed:\n{result}")

        jira_url = os.getenv("JIRA_URL")
        jira_username = os.getenv("JIRA_USERNAME")
        jira_token = os.getenv("JIRA_API_TOKEN")
        if jira_url and jira_username and jira_token:
            jira_client = JiraClient(jira_url, jira_username, jira_token)
            summary = getattr(result, "summary", "")
            if result.status == TestStatus.PASS:
                await jira_client.add_comment(
                    issue_key,
                    _format_testing_comment("✅", result, summary),
                )
                await _transition_issue_to_status(
                    jira_client,
                    issue_key,
                    ["Done", "Completed", "Resolved"],
                )
            else:
                await jira_client.add_comment(
                    issue_key,
                    _format_testing_comment("❌", result, summary),
                )
                await _transition_issue_to_status(
                    jira_client,
                    issue_key,
                    ["Waiting Development", "In Development", "To Do"],
                )
    except Exception as e:
        logger.info(f"❌ Error running tests for {issue_key}: {e}")


def _format_testing_comment(prefix: str, result: Any, summary: str) -> str:
    cases = getattr(result, "case_results", []) or []
    lines = [f"{prefix} Tests result: {summary}"]

    if cases:
        lines.append("Test Cases:")
        for case in cases:
            status = getattr(case, "status", "")
            name = getattr(case, "name", "")
            detail = getattr(case, "details", "")
            if detail:
                lines.append(f"- {status}: {name} ({detail})")
            else:
                lines.append(f"- {status}: {name}")

    err = (getattr(result, "error", "") or "").strip()
    if err:
        lines.append(f"Error: {err}")

    raw = (getattr(result, "raw_output", "") or "").strip()
    if raw:
        raw_tail = "\n".join(raw.splitlines()[-40:])
        lines.append("Test output (tail):")
        lines.append(raw_tail)

    return "\n".join(lines)


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
    logger.info(f"🧪 Testing webhook received: {request.webhookEvent}")
    
    issue = request.issue
    issue_key = issue.get("key", "")
    status = issue.get("fields", {}).get("status", {}).get("name", "")
    
    # Only process if in "Testing" status
    if status == "Testing" or status == "Test Ready":
        logger.info(f"  Running tests: {issue_key}")
        
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


# ============================================================================
# API ENDPOINTS FOR MANUAL TRIGGERING (No webhooks required)
# ============================================================================

@app.post("/api/agents/process-development")
async def api_process_development(background_tasks: BackgroundTasks):
    """
    Manually trigger processing of all 'Development Waiting' tasks.
    
    Usage:
        POST http://localhost:8000/api/agents/process-development
    
    Returns:
        - status: "started" or "no_tasks"
        - count: number of tasks found
    """
    try:
        from src.clients.jira_client import JiraClient
        
        jira_client = JiraClient(
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
        )
        
        # Find all Waiting Development tasks
        jql = 'status = "Waiting Development" AND assignee is EMPTY'
        issues = await jira_client.search_issues(jql)
        
        if not issues:
            return {
                "status": "no_tasks",
                "count": 0,
                "message": "No 'Development Waiting' tasks found"
            }
        
        # Dispatch each issue to background processing (key or id)
        issue_keys = []
        for issue in issues:
            if isinstance(issue, dict):
                issue_key = issue.get('key') or issue.get('id') or str(issue)
            else:
                issue_key = str(issue)
            if issue_key:
                issue_keys.append(issue_key)
                background_tasks.add_task(_process_jira_task_in_background, issue_key)
        
        return {
            "status": "started",
            "count": len(issue_keys),
            "message": f"Started processing {len(issue_keys)} task(s)",
            "issues": issue_keys
        }
    
    except Exception as e:
        logger.error(f"Error in api_process_development: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/process-reviews")
async def api_process_reviews(background_tasks: BackgroundTasks):
    """
    Manually trigger code review for all 'In Review' tasks.
    
    Usage:
        POST http://localhost:8000/api/agents/process-reviews
    
    Returns:
        - status: "started" or "no_tasks"
        - count: number of tasks found
    """
    try:
        from src.clients.jira_client import JiraClient
        
        jira_client = JiraClient(
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
        )
        
        # Find all review-ready tasks
        jql = 'status in ("Code Review", "In Review", "Review", "Code Ready")'
        issues = await jira_client.search_issues(jql)
        
        if not issues:
            return {
                "status": "no_tasks",
                "count": 0,
                "message": "No 'In Review' tasks found"
            }
        
        # Dispatch each issue to background processing
        for issue in issues:
            issue_key = issue.get('key')
            background_tasks.add_task(_review_code_in_background, issue_key, [])
        
        return {
            "status": "started",
            "count": len(issues),
            "message": f"Started reviewing {len(issues)} task(s)",
            "issues": [issue.get('key') for issue in issues]
        }
    
    except Exception as e:
        logger.error(f"Error in api_process_reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/process-testing")
async def api_process_testing(background_tasks: BackgroundTasks):
    """
    Manually trigger testing for all 'Testing' tasks.
    
    Usage:
        POST http://localhost:8000/api/agents/process-testing
    
    Returns:
        - status: "started" or "no_tasks"
        - count: number of tasks found
    """
    try:
        from src.clients.jira_client import JiraClient
        
        jira_client = JiraClient(
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
        )
        
        # Find all Testing tasks
        jql = 'status = "Testing"'
        issues = await jira_client.search_issues(jql)
        
        if not issues:
            return {
                "status": "no_tasks",
                "count": 0,
                "message": "No 'Testing' tasks found"
            }
        
        # Dispatch each issue to background processing
        for issue in issues:
            issue_key = issue.get('key')
            background_tasks.add_task(_run_tests_in_background, issue_key, None)
        
        return {
            "status": "started",
            "count": len(issues),
            "message": f"Started testing {len(issues)} task(s)",
            "issues": [issue.get('key') for issue in issues]
        }
    
    except Exception as e:
        logger.error(f"Error in api_process_testing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/process-all")
async def api_process_all(background_tasks: BackgroundTasks):
    """
    MVP Jira Flow:
    Jira task alır →
    development_agent →
    code_review_agent →
    testing_agent →
    test başarılıysa completed = true

    Manually trigger all agents in sequence (Development → Review → Testing).
    
    Usage:
        POST http://localhost:8000/api/agents/process-all
    
    Returns:
        - status: "started"
        - tasks: breakdown by stage
        - completed: True if testing succeeded (async result), otherwise False
    """
    try:
        from src.clients.jira_client import JiraClient
        
        jira_client = JiraClient(
            jira_url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
        )
        
        results = {
            "development_waiting": [],
            "in_review": [],
            "testing": []
        }
        
        # 1) development_agent: create/update code for Waiting Development tasks
        dev_jql = 'status = "Waiting Development" AND assignee is EMPTY'
        dev_issues = await jira_client.search_issues(dev_jql)
        for issue in dev_issues:
            issue_key = issue.get('key')
            results["development_waiting"].append(issue_key)
            background_tasks.add_task(_process_jira_task_in_background, issue_key)
        
        # 2) code_review_agent: review code for In Review tasks
        review_jql = 'status in ("Code Review", "In Review", "Review", "Code Ready")'
        review_issues = await jira_client.search_issues(review_jql)
        for issue in review_issues:
            issue_key = issue.get('key')
            results["in_review"].append(issue_key)
            background_tasks.add_task(_review_code_in_background, issue_key, [])
        
        # 3) testing_agent: run tests for Testing tasks
        test_jql = 'status = "Testing"'
        test_issues = await jira_client.search_issues(test_jql)
        for issue in test_issues:
            issue_key = issue.get('key')
            results["testing"].append(issue_key)
            background_tasks.add_task(_run_tests_in_background, issue_key, None)
        
        total = len(dev_issues) + len(review_issues) + len(test_issues)

        # Response semantics:
        # - development_waiting: Jira issues dispatched to development_agent
        # - in_review: Jira issues dispatched to code_review_agent
        # - testing: Jira issues dispatched to testing_agent
        # - completed: True only when tests succeed (async); not known at dispatch time
        completed = False
        
        return {
            "status": "started",
            "total_tasks": total,
            "tasks": results,
            "completed": completed,
            "message": f"Started processing {total} task(s) across all stages"
        }
    
    except Exception as e:
        logger.error(f"Error in api_process_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/status")
async def api_status():
    """
    Get the current status of the scheduler.
    
    Usage:
        GET http://localhost:8000/api/agents/status
    
    Returns:
        - scheduler_running: true/false
        - jobs: list of scheduled jobs
    """
    scheduler = get_scheduler()
    jobs = []
    
    if scheduler.scheduler.running:
        for job in scheduler.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger)
            })
    
    return {
        "scheduler_running": scheduler.scheduler.running,
        "total_jobs": len(jobs),
        "jobs": jobs
    }