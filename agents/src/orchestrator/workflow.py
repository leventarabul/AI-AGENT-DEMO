"""MVP Jira workflow orchestration.

Runs Development → Code Review → Testing and posts results back to Jira.
"""

import logging
import os
import subprocess
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.clients.jira_client import JiraClient
from src.agents.development_agent import DevelopmentAgent
from src.agents.code_review_agent import CodeReviewAgent, format_review_comment
from src.agents.testing_agent import TestingAgent, TestStatus

logger = logging.getLogger(__name__)


def _normalize_for_json(value: Any) -> Any:
    """Convert dataclasses and Enums into JSON-serializable structures."""
    if is_dataclass(value):
        return _normalize_for_json(asdict(value))
    if isinstance(value, dict):
        return {k: _normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


async def _add_jira_comment(
    jira_client: Any,
    issue_key: str,
    comment: str,
    dry_run: bool,
) -> None:
    """Add a Jira comment unless DRY_RUN is enabled."""
    if dry_run:
        logger.info(
            "[DRY_RUN] Skipping Jira comment for %s: %s", issue_key, comment
        )
        return
    await jira_client.add_comment(issue_key, comment)


async def _transition_issue_to_done(
    jira_client: Any,
    issue_key: str,
    dry_run: bool,
) -> bool:
    """Attempt to transition issue to Done/Closed; return True if successful."""
    target_names = ["Done", "Closed", "Complete", "Completed", "Resolved"]
    transitions = await jira_client.get_transitions(issue_key)
    for name in target_names:
        for transition in transitions:
            if transition.get("name") == name:
                if dry_run:
                    logger.info(
                        "[DRY_RUN] Skipping transition for %s to %s", issue_key, name
                    )
                    return True
                await jira_client.transition_issue(issue_key, transition_id=transition.get("id"))
                return True
    return False


def _collect_code_files_from_repo(repo_root: str) -> List[Tuple[str, str]]:
    """Collect changed files from git for review.

    Returns a list of (file_path, content) tuples.
    """
    if not os.path.exists(os.path.join(repo_root, ".git")):
        logger.warning("Repo not found at %s; skipping git diff", repo_root)
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


async def run_mvp_jira_flow(
    issue_key: str,
    payload: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run MVP Jira flow: Development → Code Review → Testing with Jira feedback."""
    env_dry_run = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes"}
    dry_run = dry_run or env_dry_run
    errors: List[str] = []
    payload = payload or {}

    logger.info("Starting MVP Jira flow for %s", issue_key)

    jira_client = JiraClient(
        jira_url=os.getenv("JIRA_URL"),
        username=os.getenv("JIRA_USERNAME"),
        api_token=os.getenv("JIRA_API_TOKEN"),
    )

    issue = await jira_client.get_issue(issue_key, fields="summary,description,status")
    fields = issue.get("fields", {}) if isinstance(issue, dict) else {}
    summary = fields.get("summary", "")
    description = fields.get("description", "")

    # 1) DevelopmentAgent
    development_agent = DevelopmentAgent(repo_root=os.getenv("GIT_REPO_PATH", "."))
    development_context = {
        "jira_issue_key": issue_key,
        "jira_issue_status": fields.get("status", {}).get("name", "Development"),
        "code_changes": payload.get("code_changes", {}),
        "summary": summary,
        "description": description,
    }
    development_result = development_agent.execute(development_context)
    if not development_result.success:
        errors.append(development_result.error or "Development failed")

    logger.info(
        "Development completed for %s (success=%s)",
        issue_key,
        development_result.success,
    )

    development_summary = (
        f"Development output: success={development_result.success}, "
        f"files={len(development_result.files)}, "
        f"commit_message='{development_result.commit_message}'"
    )
    await _add_jira_comment(jira_client, issue_key, development_summary, dry_run)

    # 2) CodeReviewAgent (with repo fallback)
    code_review_agent = CodeReviewAgent(repo_root=os.getenv("GIT_REPO_PATH", "."))
    code_files: List[Tuple[str, str]] = []
    if development_result.files:
        code_files = [(f.path, f.content) for f in development_result.files]
    if not code_files:
        code_files = _collect_code_files_from_repo(os.getenv("GIT_REPO_PATH", "."))
    review_result = await code_review_agent.review_pull_request(issue_key, code_files)
    if not review_result.success:
        errors.append(review_result.error or "Code review failed")

    logger.info(
        "Code review completed for %s (success=%s, decision=%s)",
        issue_key,
        review_result.success,
        review_result.decision,
    )

    review_summary = f"Code review summary:\n{format_review_comment(review_result)}"
    await _add_jira_comment(jira_client, issue_key, review_summary, dry_run)

    # 3) TestingAgent
    testing_agent = TestingAgent(repo_root=os.getenv("GIT_REPO_PATH", "."))
    testing_result = testing_agent.execute({"test_path": "tests/"})
    if not testing_result.success:
        errors.append(testing_result.error or "Testing failed")

    logger.info(
        "Testing completed for %s (success=%s, status=%s)",
        issue_key,
        testing_result.success,
        testing_result.status,
    )

    testing_summary = (
        f"Test summary: status={testing_result.status.value}, "
        f"passed={testing_result.passed_count}, failed={testing_result.failed_count}, "
        f"summary='{testing_result.summary}'"
    )
    await _add_jira_comment(jira_client, issue_key, testing_summary, dry_run)

    completed = testing_result.success and testing_result.status == TestStatus.PASS
    if completed:
        transitioned = await _transition_issue_to_done(jira_client, issue_key, dry_run)
        if not transitioned:
            await _add_jira_comment(
                jira_client,
                issue_key,
                "manual transition needed: no Done/Closed transition found. "
                "Please transition the issue manually in Jira.",
                dry_run,
            )

    return {
        "issue_key": issue_key,
        "development": _normalize_for_json(development_result),
        "review": _normalize_for_json(review_result),
        "testing": _normalize_for_json(testing_result),
        "completed": completed,
        "errors": errors,
    }
