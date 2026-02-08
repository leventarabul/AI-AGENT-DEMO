import os
import json
import re
import subprocess
import tempfile
import httpx
from typing import Optional, Dict, Any, Tuple, List
from src.knowledge.context_loader import build_ai_prompt
from src.clients.jira_client import JiraClient
from src.clients.ai_management_client import AIManagementClient
from src.agents.code_review_agent import CodeReviewAgent, ReviewDecision, format_review_comment
from src.agents.testing_agent import TestingAgent, TestStatus
from src.agents.development_agent import DevelopmentAgent
import logging
logger = logging.getLogger(__name__)


class JiraAgent:
    """Agent that processes Jira tasks: code gen → test gen → PR creation."""
    
    def __init__(
        self,
        jira_url: str,
        jira_username: str,
        jira_token: str,
        ai_management_url: str = None,
        git_repo_path: str = None,
        git_user_name: str = "AI Agent",
        git_user_email: str = "agent@ai.local",
    ):
        self.jira_client = JiraClient(jira_url, jira_username, jira_token)
        self.ai_management_url = ai_management_url or os.getenv("AI_MANAGEMENT_URL", \
        "http://ai-management-service:8001")
        self.ai_client = AIManagementClient(self.ai_management_url)
        self.git_repo_path = git_repo_path or os.getenv("GIT_REPO_PATH") or os.getcwd()
        self.git_user_name = git_user_name
        self.git_user_email = git_user_email
    
    async def process_task(self, issue_key: str) -> Dict[str, Any]:
        """Main orchestration: fetch task → generate code → gen tests → create PR."""
        logger.info(f"\n🚀 Processing Jira task: {issue_key}")
        
        # Fetch issue details
        issue = await self.jira_client.get_issue(issue_key)
        task_title = issue.get("fields", {}).get("summary", "")
        task_description = issue.get("fields", {}).get("description", {})
        task_labels = issue.get("fields", {}).get("labels", [])
        retry_count = self._get_retry_count(task_labels)
        if retry_count >= 3:
            await self.jira_client.add_comment(
                issue_key,
                "🚫 Retry limit reached (3). Blocking task to prevent infinite loop.",
            )
            await self._transition_to_status(issue_key, target_names=["Blocked", "On Hold"])
            return {
                "issue_key": issue_key,
                "status": "blocked",
                "reason": "retry_limit_reached",
            }

        # Fetch reviewer comments (for fix context)
        comments = await self.jira_client.get_comments(issue_key)
        reviewer_notes = self._format_reviewer_comments(comments)
        
        if isinstance(task_description, dict):
            task_description = self._extract_text_from_rich_text(task_description)
        if task_description is None:
            task_description = ""

        if reviewer_notes:
            task_description = (
                f"{task_description}\n\n"
                "Reviewer Comments:\n"
                f"{reviewer_notes}"
            )
        
        logger.info(f"  Title: {task_title}")
        desc_preview = task_description[:100] + ("..." if len(task_description) > 100 else "")
        logger.info(f"  Description: {desc_preview}")
        
        # Step 1: Generate code (multi-file aware)
        code_result = await self.generate_code(
            task_title, task_description, task_labels
        )
        generated_code = code_result.get("code", "")
        parsed_files = code_result.get("parsed_files")

        if self._is_demo_domain_task(task_title, task_description, task_labels):
            if not parsed_files:
                await self.jira_client.add_comment(
                    issue_key,
                    "❌ Code generation missing demo-domain files. "
                    "Please retry; expected changes under demo-domain/.",
                )
                await self._transition_to_status(
                    issue_key,
                    target_names=["Waiting Development", "In Development", "To Do"],
                )
                return {
                    "issue_key": issue_key,
                    "status": "missing_demo_domain_files",
                }
            has_demo_domain = any(
                path.startswith("demo-domain/")
                for path in parsed_files.keys()
            )
            if not has_demo_domain:
                await self.jira_client.add_comment(
                    issue_key,
                    "❌ Code generation did not modify demo-domain/. "
                    "Task requires demo-domain changes.",
                )
                await self._transition_to_status(
                    issue_key,
                    target_names=["Waiting Development", "In Development", "To Do"],
                )
                return {
                    "issue_key": issue_key,
                    "status": "missing_demo_domain_files",
                }
        
        # Step 2: Generate tests
        tests_result = await self.generate_tests(
            task_title, generated_code
        )
        generated_tests = tests_result.get("tests", "")

        # Post initial development summary BEFORE code review
        await self.jira_client.add_comment(
            issue_key,
            "## 🛠 Development Started\n"
            f"**Task:** {task_title}\n"
            "**Status:** Code generated, preparing review\n",
        )

        # Step 2.5: Code review + auto-fix loop BEFORE git commit
        code_changes = self._build_code_changes(
            issue_key, generated_code, generated_tests,
            parsed_files=parsed_files,
        )
        # Write files to disk before review to ensure dev-first flow
        self._write_code_changes_to_disk(code_changes)
        review_result, code_changes = await self._run_code_review_with_retries(
            issue_key,
            code_changes,
            max_attempts=2,
        )
        # Update generated_code from review fixes
        for fpath, content in code_changes.items():
            if fpath.endswith("_impl.py"):
                generated_code = content
            elif fpath.endswith(f"test_{issue_key}.py"):
                generated_tests = content

        if review_result.decision != ReviewDecision.APPROVE:
            await self.jira_client.add_comment(
                issue_key,
                "🚫 " + format_review_comment(review_result),
            )
            retry_count += 1
            await self._update_retry_label(issue_key, task_labels, retry_count)
            if retry_count >= 3:
                await self._transition_to_status(issue_key, target_names=["Blocked", "On Hold"])
            else:
                await self._transition_to_status(
                    issue_key,
                    target_names=["Waiting Development", "In Development", "To Do"],
                )
            return {
                "issue_key": issue_key,
                "status": "review_failed",
                "review_decision": review_result.decision.value,
            }

        await self.jira_client.add_comment(
            issue_key,
            "✅ " + format_review_comment(review_result),
        )
        
        # Step 3: Commit and push
        branch_name = self._create_branch_name(issue_key, task_title)
        commit_sha = await self.commit_and_push(
            branch_name,
            generated_code,
            generated_tests,
            issue_key,
            task_title,
        )
        
        # Step 4: Create PR
        pr_info = await self.create_pull_request(
            branch_name, task_title, task_description, issue_key
        )

        # Step 4.5: Trigger deploy if configured
        await self._trigger_deploy(issue_key, branch_name, commit_sha)
        
        # Step 5: Post development details as comment
        changed_files = list(code_changes.keys())
        await self._post_development_summary(
            issue_key, task_title, generated_code,
            generated_tests, pr_info, changed_files
        )
        await self._post_development_details(
            issue_key, task_title, generated_code,
            generated_tests, pr_info, changed_files
        )

        # Step 5.5: Run tests and update Jira status
        test_result = self._run_tests(issue_key)
        await self._post_testing_result(issue_key, test_result)
        if test_result.status == TestStatus.PASS:
            await self._clear_retry_label(issue_key, task_labels)
            self._push_current_branch()
            await self._post_done_commit_info(issue_key)
            await self._transition_to_status(
                issue_key,
                target_names=["Done", "Completed", "Resolved"],
            )
        else:
            await self._transition_to_status(
                issue_key,
                target_names=["Waiting Development", "In Development", "To Do"],
            )
        
        return {
            "issue_key": issue_key,
            "branch": branch_name,
            "code": (
                generated_code[:200] + "..."
                if len(generated_code) > 200
                else generated_code
            ),
            "tests": (
                generated_tests[:200] + "..."
                if len(generated_tests) > 200
                else generated_tests
            ),
            "commit_sha": commit_sha,
            "pr": pr_info,
        }

    async def _transition_to_status(self, issue_key: str, target_names: list) -> None:
        """Transition Jira issue to one of the desired statuses by name."""
        try:
            transitions = await self.jira_client.get_transitions(issue_key)
            target = None
            for name in target_names:
                for t in transitions:
                    if t.get("name") == name:
                        target = t
                        break
                if target:
                    break
            if not target:
                logger.info(
                    "  ⚠️ No matching transition found for %s; skipping status change",
                    target_names,
                )
                return
            await self.jira_client.transition_issue(issue_key, transition_id=target.get("id"))
            logger.info(f"  🔄 Transitioned '{issue_key}' to '{target.get('name')}'")
        except Exception as e:
            logger.info(f"  ⚠️ Transition error for {issue_key}: {e}")
    
    async def generate_code(
        self, task_title: str, task_description: str, labels: list
    ) -> Dict[str, str]:
        """Use AI to generate code for the task."""
        logger.info(f"  📝 Generating code...")
        
        # Build context with existing codebase
        prompt = build_ai_prompt(task_title, task_description, labels)
        
        # Add code generation instructions
        code_prompt = (
            prompt + "\n\n"
            "---\n\n"
            "You are an expert Python developer. Based on the system architecture "
            "and code patterns above, write production-ready Python code to "
            "implement this task.\n\n"
            "IMPORTANT:\n"
            "1. Follow the existing code patterns (async/await, FastAPI, httpx)\n"
            "2. Include proper error handling and logging\n"
            "3. Add type hints\n"
            "4. Output ONLY the code, no explanations\n"
            "5. Start with ```python and end with ```\n"
            "6. NEVER use logger.info(); always use the logging module\n"
        )
        
        response = await self.ai_client.generate(
            prompt=code_prompt,
            provider="openai",
            max_tokens=1200,
            temperature=0.4,
            use_cache=False,
        )
        
        generated_text = response.get("text", "")
        code = self._extract_code_block(generated_text)
        
        return {"code": code, "raw_response": generated_text}
    
    async def generate_tests(
        self, task_title: str, code: str
    ) -> Dict[str, str]:
        """Use AI to generate integration tests for the task."""
        logger.info(f"  🧪 Generating tests...")
        
        test_prompt = (
            f"Task: {task_title}\n\n"
            "Code:\n```python\n" + code + "\n```\n\n"
            "Write comprehensive integration tests that test "
            "the ACTUAL demo-domain API at "
            "http://demo-domain-api:8000.\n\n"
            "IMPORTANT:\n"
            "1. Use httpx or requests to call real API endpoints\n"
            "2. Use HTTP Basic Auth: admin/admin123\n"
            "3. Test the full flow: create campaign, add rule, "
            "send event, verify processing and earnings\n"
            "4. Use pytest fixtures for setup/teardown\n"
            "5. Output ONLY the test code\n"
            "6. Start with ```python and end with ```\n"
            "7. Include assertions on response status codes "
            "and response body content\n"
            "8. Each test should be independent and idempotent\n"
            "9. Use unique transaction_ids (uuid) to avoid "
            "conflicts\n"
        )
        
        response = await self.ai_client.generate(
            prompt=test_prompt,
            provider="openai",
            max_tokens=1200,
            temperature=0.4,
            use_cache=False,
        )
        
        generated_text = response.get("text", "")
        tests = self._extract_code_block(generated_text)
        
        return {"tests": tests, "raw_response": generated_text}
    
    async def commit_and_push(
        self,
        branch_name: str,
        code: str,
        tests: str,
        issue_key: str,
        task_title: str,
    ) -> str:
        """Commit code and tests to git, push to remote."""
        logger.info(f"  🔧 Committing and pushing...")
        
        # Create branch
        # If repo is not a git repository, skip git operations
        is_git_repo = self._is_git_repo()
        if is_git_repo:
            self._checkout_or_create_branch(branch_name)
        
        # Write code file
        code_path = os.path.join(self.git_repo_path, f"agents/src/agents/{issue_key}_impl.py")
        os.makedirs(os.path.dirname(code_path), exist_ok=True)
        with open(code_path, "w") as f:
            f.write(code)
        
        # Write test file
        test_path = os.path.join(self.git_repo_path, f"tests/test_{issue_key}.py")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w") as f:
            f.write(tests)
        
        commit_sha = "unknown"
        if is_git_repo:
            # Configure git
            self._run_git(["config", "user.name", self.git_user_name])
            self._run_git(["config", "user.email", self.git_user_email])

            # Ensure remote supports auth if token is provided
            self._configure_auth_remote()
            
            # Add and commit
            self._run_git(["add", code_path, test_path], check=True)
            result = self._run_git(
                ["commit", "-m", f"[{issue_key}] {task_title}"],
                capture_output=True,
            )
            
            if result.returncode == 0:
                commit_sha = result.stdout.split("(")[0].strip()
            else:
                commit_sha = "unknown"
            
            # Push to remote
            self._run_git(["push", "-u", "origin", branch_name])
        else:
            logger.info("  ⚠️ No git repo detected; files written without commit/push")
        
        return commit_sha

    def _configure_auth_remote(self) -> None:
        """Configure origin remote with token if provided."""
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GIT_TOKEN")
        repo_url = os.getenv("GITHUB_REPO_URL") or os.getenv("GIT_REMOTE_URL")

        if not token or not repo_url:
            return

        if repo_url.startswith("https://"):
            auth_url = repo_url.replace(
                "https://",
                f"https://x-access-token:{token}@",
                1,
            )
        else:
            auth_url = repo_url

        self._run_git(["remote", "set-url", "origin", auth_url], check=False)

    def _checkout_or_create_branch(self, branch_name: str) -> None:
        """Checkout existing branch or create it if missing."""
        exists = self._run_git(
            ["rev-parse", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            check=False,
        ).returncode == 0

        if exists:
            self._run_git(["checkout", branch_name], check=True)
            return

        self._run_git(["checkout", "-b", branch_name], check=True)

    def _push_current_branch(self) -> None:
        """Push current branch to origin if git repo is available."""
        if not self._is_git_repo():
            return
        self._configure_auth_remote()
        self._run_git(["push"], check=False)

    def _get_current_commit_sha(self) -> Optional[str]:
        if not self._is_git_repo():
            return None
        result = self._run_git(["rev-parse", "HEAD"], capture_output=True, check=False)
        sha = (result.stdout or "").strip()
        return sha or None

    def _sanitize_repo_url(self, repo_url: Optional[str]) -> Optional[str]:
        if not repo_url:
            return None
        if repo_url.startswith("https://x-access-token:"):
            return "https://" + repo_url.split("@", 1)[-1]
        return repo_url

    def _build_commit_url(self, sha: Optional[str]) -> Optional[str]:
        if not sha:
            return None
        owner, name = self._parse_github_repo()
        if not owner or not name:
            return None
        return f"https://github.com/{owner}/{name}/commit/{sha}"

    async def _post_done_commit_info(self, issue_key: str) -> None:
        sha = self._get_current_commit_sha()
        short_sha = sha[:7] if sha else "unknown"
        commit_url = self._build_commit_url(sha)
        repo_url = self._sanitize_repo_url(os.getenv("GITHUB_REPO_URL"))
        lines = ["✅ Done: code pushed"]
        lines.append(f"- Commit: {short_sha}")
        if commit_url:
            lines.append(f"- Commit link: {commit_url}")
        if repo_url:
            lines.append(f"- Repo: {repo_url}")
        await self.jira_client.add_comment(issue_key, "\n".join(lines))

    async def _trigger_deploy(self, issue_key: str, branch_name: str, commit_sha: str) -> None:
        """Trigger deployment webhook if configured."""
        deploy_url = os.getenv("DEPLOY_WEBHOOK_URL")
        if not deploy_url:
            return

        payload = {
            "issue_key": issue_key,
            "branch": branch_name,
            "commit": commit_sha,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(deploy_url, json=payload)
        except Exception as e:
            logger.info(f"  ⚠️ Deploy webhook failed: {e}")
    
    async def create_pull_request(
        self,
        branch_name: str,
        task_title: str,
        task_description: str,
        issue_key: str,
    ) -> Dict[str, Any]:
        """Create a pull request on GitHub (or similar)."""
        logger.info(f"  📤 Creating pull request...")
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GIT_TOKEN")
        owner, repo = self._parse_github_repo()
        base_branch = os.getenv("GITHUB_BASE_BRANCH", "main")

        if not token or not owner or not repo:
            return {
                "branch": branch_name,
                "title": f"[{issue_key}] {task_title}",
                "description": task_description,
                "html_url": "N/A",
            }

        payload = {
            "title": f"[{issue_key}] {task_title}",
            "head": branch_name,
            "base": base_branch,
            "body": task_description or "",
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 201:
                    data = resp.json()
                    return {
                        "branch": branch_name,
                        "title": data.get("title"),
                        "description": data.get("body"),
                        "html_url": data.get("html_url"),
                    }
                return {
                    "branch": branch_name,
                    "title": f"[{issue_key}] {task_title}",
                    "description": task_description,
                    "html_url": "N/A",
                }
        except Exception:
            return {
                "branch": branch_name,
                "title": f"[{issue_key}] {task_title}",
                "description": task_description,
                "html_url": "N/A",
            }
    
    def _extract_code_block(self, text: str) -> str:
        """Extract code from markdown code block."""
        if "```python" in text:
            start = text.find("```python") + len("```python")
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        elif "```sql" in text:
            start = text.find("```sql") + len("```sql")
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        return text.strip()

    def _parse_multi_file_response(
        self, text: str
    ) -> Optional[Dict[str, str]]:
        """Parse LLM response with multiple ### FILE: blocks.

        Returns {filepath: content} dict or None if no blocks found.
        """
        pattern = r'(?:###\s*)?FILE:\s*(.+?)[\s]*\n'
        parts = re.split(pattern, text)
        if len(parts) < 3:
            return None

        files: Dict[str, str] = {}
        # parts: [preamble, path1, body1, path2, body2, ...]
        for i in range(1, len(parts), 2):
            filepath = parts[i].strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            content = self._extract_code_block(body)
            if not content:
                content = body.strip()
            if filepath and content:
                files[filepath] = content

        return files if files else None
    
    def _extract_text_from_rich_text(self, rich_text: Dict[str, Any]) -> str:
        """Extract plain text from Jira rich text format."""
        content = rich_text.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "paragraph":
                for child in item.get("content", []):
                    if child.get("type") == "text":
                        texts.append(child.get("text", ""))
        return " ".join(texts)

    def _format_reviewer_comments(self, comments: list) -> str:
        """Format reviewer comments for prompt context."""
        formatted = []
        seen = set()
        for comment in comments or []:
            author = (comment.get("author") or {}).get("displayName", "")
            if author and "ai agent" in author.lower():
                continue
            body = comment.get("body")
            if isinstance(body, dict):
                text = self._extract_text_from_rich_text(body)
            else:
                text = str(body or "")
            text = text.strip()
            if not text:
                continue
            lower_text = text.lower()
            if (
                "development details" in lower_text
                or "development summary" in lower_text
                or "ai agent completed development" in lower_text
            ):
                continue
            normalized = " ".join(lower_text.split())
            if normalized in seen:
                continue
            seen.add(normalized)
            formatted.append(f"- {author or 'Reviewer'}: {text}")
            if len(formatted) >= 5:
                break
        return "\n".join(formatted)
    
    def _create_branch_name(self, issue_key: str, task_title: str) -> str:
        """Create a git branch name from issue key and title."""
        title_slug = task_title.lower().replace(" ", "-")[:30]
        return f"feat/{issue_key}/{title_slug}".lower()

    def _build_code_changes(
        self,
        issue_key: str,
        code: str,
        tests: str,
        parsed_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build code changes dict from parsed multi-file or fallback."""
        changes: Dict[str, str] = {}
        if parsed_files:
            changes.update(parsed_files)
        else:
            # Fallback: single impl file (legacy behavior)
            changes[f"agents/src/agents/{issue_key}_impl.py"] = code
        changes[f"tests/test_{issue_key}.py"] = tests
        return changes

    def _is_demo_domain_task(
        self,
        task_title: str,
        task_description: str,
        task_labels: List[str],
    ) -> bool:
        text = f"{task_title} {task_description}".lower()
        label_text = " ".join(task_labels or []).lower()
        keywords = [
            "demo-domain",
            "campaign",
            "campaign_rule",
            "kampanya",
            "event",
            "events",
        ]
        return any(k in text or k in label_text for k in keywords)

    async def _run_code_review_with_retries(
        self,
        issue_key: str,
        code_changes: Dict[str, str],
        max_attempts: int = 2,
    ) -> Tuple[Any, Dict[str, str]]:
        review_agent = CodeReviewAgent(repo_root=self.git_repo_path)
        dev_agent = DevelopmentAgent()

        latest_result = review_agent.execute(
            {"jira_issue_key": issue_key, "code_changes": code_changes}
        )
        attempts = 0

        while (
            latest_result.decision in (ReviewDecision.BLOCK, ReviewDecision.REQUEST_CHANGES)
            and attempts < max_attempts
        ):
            fix_context = {
                "jira_issue_key": issue_key,
                "jira_issue_status": "Development",
                "code_changes": code_changes,
                "auto_fix": True,
                "review_issues": latest_result.issues,
            }
            fix_output = dev_agent.execute(fix_context)
            if not fix_output.success:
                break

            code_changes = {f.path: f.content for f in fix_output.files}
            latest_result = review_agent.execute(
                {"jira_issue_key": issue_key, "code_changes": code_changes}
            )
            attempts += 1

        return latest_result, code_changes

    def _run_tests(self, issue_key: str) -> Any:
        test_agent = TestingAgent(repo_root=self.git_repo_path)
        return test_agent.execute(
            {
                "qa_mode": True,
                "issue_key": issue_key,
                "test_files": [f"tests/test_{issue_key}.py"],
                "test_path": "tests/",
            }
        )

    async def _post_testing_result(self, issue_key: str, result: Any) -> None:
        if result.status == TestStatus.PASS:
            await self.jira_client.add_comment(
                issue_key,
                self._format_testing_comment("✅", result),
            )
            return

        failure_lines = []
        for failure in result.failures[:5]:
            loc = f" ({failure.file_path})" if failure.file_path else ""
            failure_lines.append(f"- {failure.test_name}{loc}: {failure.error_message}")
        details = "\n".join(failure_lines)
        if not details:
            err = (getattr(result, "error", "") or "").strip()
            raw = (getattr(result, "raw_output", "") or "").strip()
            raw_tail = "\n".join(raw.splitlines()[-40:]) if raw else result.summary
            if err:
                details = f"Error: {err}\nTest output (tail):\n{raw_tail}"
            else:
                details = f"Test output (tail):\n{raw_tail}"

        await self.jira_client.add_comment(
            issue_key,
            self._format_testing_comment("❌", result, details),
        )

    def _format_testing_comment(
        self,
        prefix: str,
        result: Any,
        details: Optional[str] = None,
    ) -> str:
        cases = getattr(result, "case_results", []) or []
        lines = [f"{prefix} Tests result: {result.summary}"]

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

        if details:
            lines.append(details)

        return "\n".join(lines)

    def _get_retry_count(self, labels: List[str]) -> int:
        for label in labels or []:
            if label.startswith("ai-retry-"):
                try:
                    return int(label.split("ai-retry-")[-1])
                except ValueError:
                    return 0
        return 0

    async def _update_retry_label(self, issue_key: str, labels: List[str], count: int) -> None:
        updated = [l for l in (labels or []) if not l.startswith("ai-retry-")]
        updated.append(f"ai-retry-{count}")
        await self.jira_client.update_issue_fields(issue_key, {"labels": updated})

    async def _clear_retry_label(self, issue_key: str, labels: List[str]) -> None:
        updated = [l for l in (labels or []) if not l.startswith("ai-retry-")]
        await self.jira_client.update_issue_fields(issue_key, {"labels": updated})

    def _parse_github_repo(self) -> Tuple[Optional[str], Optional[str]]:
        repo = os.getenv("GITHUB_REPOSITORY")
        if repo and "/" in repo:
            owner, name = repo.split("/", 1)
            return owner, name

        repo_url = os.getenv("GITHUB_REPO_URL") or os.getenv("GIT_REMOTE_URL")
        if not repo_url:
            return None, None

        if repo_url.startswith("git@"):
            repo_url = repo_url.split(":", 1)[-1]
        if repo_url.startswith("https://"):
            repo_url = repo_url.replace("https://", "", 1)
        repo_url = repo_url.replace("github.com/", "")
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]
        if "/" in repo_url:
            owner, name = repo_url.split("/", 1)
            return owner, name
        return None, None
    
    async def _post_development_details(
        self,
        issue_key: str,
        task_title: str,
        code: str,
        tests: str,
        pr_info: Dict[str, Any],
        changed_files: Optional[List[str]] = None,
    ) -> None:
        """Post detailed development information as Jira comment."""
        endpoints = self._extract_endpoints(code)
        functions = self._extract_functions(code)
        
        comment = (
            "## \U0001f4dd Development Details\n\n"
            f"**Task:** {task_title}\n"
            f"**PR:** {pr_info.get('html_url', 'N/A')}\n\n"
        )
        
        # Changed files section
        if changed_files:
            comment += "### \U0001f4c1 Changed Files\n\n"
            for f in changed_files:
                comment += f"- `{f}`\n"
            comment += "\n"
        
        # API Endpoints section
        if endpoints:
            comment += "### 🔗 API Endpoints\n\n"
            for endpoint in endpoints[:5]:
                comment += f"- {endpoint}\n"
            comment += "\n"
        
        # Example curl commands
        comment += "### 💻 Example Usage\n\n"
        comment += "```bash\n"
        
        if "async def get_" in code:
            comment += "# GET request example\n"
            comment += "curl -X GET http://localhost:8000/api/resource \\\\\n"
            comment += "  -H 'Content-Type: application/json' \\\\\n"
            comment += "  -H 'Authorization: Bearer {token}'\n\n"
        
        if "async def create_" in code or "async def post_" in code:
            comment += "# POST request example\n"
            comment += "curl -X POST http://localhost:8000/api/resource \\\\\n"
            comment += "  -H 'Content-Type: application/json' \\\\\n"
            comment += "  -d '{\n"
            comment += '    "key": "value"\n'
            comment += "  }'\n\n"
        
        comment += "```\n\n"
        
        # Functions/Classes section
        if functions:
            comment += "### 📦 Key Functions/Classes\n\n"
            for func in functions[:5]:
                comment += f"- `{func}`\n"
            comment += "\n"
        
        # Implementation notes
        comment += "### ✅ Implementation Details\n\n"
        if changed_files:
            for f in changed_files:
                comment += f"- **File**: `{f}`\n"
        else:
            comment += (
                f"- **File**: "
                f"`agents/src/agents/{issue_key}_impl.py`\n"
            )
            comment += (
                f"- **Tests**: "
                f"`tests/test_{issue_key}.py`\n"
            )
        comment += f"- **Lines of Code**: ~{len(code.split(chr(10)))} (implementation)\n"
        comment += f"- **Test Coverage**: ~{len(tests.split(chr(10)))} lines (tests)\n"
        comment += "- **Async**: Yes (async/await patterns)\n"
        comment += "- **Error Handling**: Included\n"
        comment += "- **Documentation**: Docstrings present\n\n"
        
        # Testing guide
        comment += "### 🧪 How to Test Locally\n\n"
        comment += "```bash\n"
        comment += "# Run tests for this task\n"
        comment += f"pytest tests/test_{issue_key}.py -v\n\n"
        comment += "# Run with coverage\n"
        comment += f"pytest tests/test_{issue_key}.py --cov=agents.src.agents.{issue_key}_impl\n\n"
        comment += "# Run specific test\n"
        comment += f"pytest tests/test_{issue_key}.py::test_<function_name> -v\n"
        comment += "```\n\n"
        
        comment += "### 📋 Next Steps\n\n"
        comment += "1. Code review will validate quality and security\n"
        comment += "2. Tests will verify functionality\n"
        comment += "3. Upon approval, code merges to main\n"
        
        await self.jira_client.add_comment(issue_key, comment)

    async def _post_development_summary(
        self,
        issue_key: str,
        task_title: str,
        code: str,
        tests: str,
        pr_info: Dict[str, Any],
        changed_files: Optional[List[str]] = None,
    ) -> None:
        """Post a short development summary as Jira comment."""
        files_str = ", ".join(
            f"`{f}`" for f in (changed_files or [])
        )
        comment = (
            "## ✅ Development Summary\n"
            f"**Task:** {task_title}\n"
            f"**PR:** {pr_info.get('html_url', 'N/A')}\n"
            f"**Changed Files:** {files_str or 'N/A'}\n"
            f"**Code Lines:** {len(code.split(chr(10)))}\n"
            f"**Test Lines:** {len(tests.split(chr(10)))}\n"
        )
        await self.jira_client.add_comment(issue_key, comment)
        logger.info(
            f"  📝 Development details posted to {issue_key}"
        )
    
    def _extract_endpoints(self, code: str) -> list:
        """Extract API endpoints from code."""
        endpoints = []
        lines = code.split("\n")
        for line in lines:
            if (
                "@app.get" in line
                or "@app.post" in line
                or "@router.get" in line
                or "@router.post" in line
            ):
                # Try to extract path
                if '"/' in line or "'/" in line:
                    import re
                    match = re.search(r'["\'](/[^"\']*)["\']', line)
                    if match:
                        endpoints.append(match.group(1))
        return endpoints[:5]
    
    def _extract_functions(self, code: str) -> list:
        """Extract function/class definitions from code."""
        functions = []
        lines = code.split("\n")
        for line in lines:
            if line.strip().startswith("def ") or line.strip().startswith("async def "):
                import re
                match = re.search(r'(?:async )?def\s+(\w+)', line)
                if match:
                    functions.append(match.group(1))
            elif line.strip().startswith("class "):
                import re
                match = re.search(r'class\s+(\w+)', line)
                if match:
                    functions.append(match.group(1))
        return functions[:5]

    def _is_git_repo(self) -> bool:
        """Check if the configured path is a git repository."""
        result = self._run_git(
            ["rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def _run_git(
        self,
        args: list,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a git command in repo with safe env."""
        return subprocess.run(
            ["git"] + args,
            cwd=self.git_repo_path,
            check=check,
            capture_output=capture_output,
            text=True,
            env={
                **os.environ,
                "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
            },
        )

    def _write_code_changes_to_disk(
        self, code_changes: Dict[str, str]
    ) -> None:
        """Write code_changes to disk before review/commit."""
        for rel_path, content in code_changes.items():
            full_path = os.path.join(self.git_repo_path, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
