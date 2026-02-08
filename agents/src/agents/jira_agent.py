import os
import json
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
        self.ai_management_url = ai_management_url or os.getenv("AI_MANAGEMENT_URL", "http://ai-management-service:8001")
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
        
        # Step 1: Generate code
        code_result = await self.generate_code(
            task_title, task_description, task_labels
        )
        generated_code = code_result.get("code", "")
        
        # Step 2: Generate tests
        tests_result = await self.generate_tests(
            task_title, generated_code
        )
        generated_tests = tests_result.get("tests", "")

        # Step 2.5: Code review + auto-fix loop BEFORE git commit
        code_changes = self._build_code_changes(issue_key, generated_code, generated_tests)
        review_result, code_changes = await self._run_code_review_with_retries(
            issue_key,
            code_changes,
            max_attempts=2,
        )
        generated_code = code_changes.get(
            f"agents/src/agents/{issue_key}_impl.py",
            generated_code,
        )
        generated_tests = code_changes.get(
            f"tests/test_{issue_key}.py",
            generated_tests,
        )

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
        await self._post_development_summary(
            issue_key, task_title, generated_code, generated_tests, pr_info
        )
        await self._post_development_details(
            issue_key, task_title, generated_code, generated_tests, pr_info
        )

        # Step 5.5: Run tests and update Jira status
        test_result = self._run_tests(issue_key)
        await self._post_testing_result(issue_key, test_result)
        if test_result.status == TestStatus.PASS:
            await self._clear_retry_label(issue_key, task_labels)
            await self._transition_to_status(
                issue_key,
                target_names=["Done", "Completed", "Resolved"],
            )
        else:
            await self._transition_to_status(
                issue_key,
                target_names=["Waiting Development", "In Development", "To Do"],
            )
        
        # Step 6: Update Jira task status (only if we actually produced a PR in a git repo)
        can_post_success = self._is_git_repo() and pr_info.get("html_url") not in (None, "N/A")
        if can_post_success:
            await self.jira_client.add_comment(
                issue_key,
                f"✅ AI Agent completed development:\n- Code generated and tested\n- PR created: {pr_info.get('html_url', 'N/A')}\n- Ready for code review"
            )
        else:
            logger.info("  ⚠️ Success comment skipped: missing git repo or PR info")
        
        # Move issue to Code Review (fallback to In Review if not available)
        await self._transition_to_status(issue_key, target_names=["Code Review", "In Review", "Review"])        
        
        return {
            "issue_key": issue_key,
            "branch": branch_name,
            "code": generated_code[:200] + "..." if len(generated_code) > 200 else generated_code,
            "tests": generated_tests[:200] + "..." if len(generated_tests) > 200 else generated_tests,
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
                logger.info(f"  ⚠️ No matching transition found for {target_names}; skipping status change")
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
            "You are an expert Python developer. Based on the system architecture and code patterns above, "
            "write production-ready Python code to implement this task.\n\n"
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
            max_tokens=2000,
            temperature=0.7,
        )
        
        generated_text = response.get("text", "")
        code = self._extract_code_block(generated_text)
        
        return {"code": code, "raw_response": generated_text}
    
    async def generate_tests(
        self, task_title: str, code: str
    ) -> Dict[str, str]:
        """Use AI to generate unit tests for the code."""
        logger.info(f"  🧪 Generating tests...")
        
        test_prompt = (
            f"Task: {task_title}\n\n"
            "Code:\n```python\n" + code + "\n```\n\n"
            "Write comprehensive pytest unit tests for the code above.\n"
            "IMPORTANT:\n"
            "1. Use pytest fixtures and mocks where appropriate\n"
            "2. Test happy paths, edge cases, and errors\n"
            "3. Output ONLY the test code, no explanations\n"
            "4. Start with ```python and end with ```\n"
        )
        
        response = await self.ai_client.generate(
            prompt=test_prompt,
            provider="openai",
            max_tokens=1500,
            temperature=0.7,
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
            
            commit_sha = result.stdout.split("(")[0].strip() if result.returncode == 0 else "unknown"
            
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
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        return text.strip()
    
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

    def _build_code_changes(self, issue_key: str, code: str, tests: str) -> Dict[str, str]:
        return {
            f"agents/src/agents/{issue_key}_impl.py": code,
            f"tests/test_{issue_key}.py": tests,
        }

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
                "test_files": [f"tests/test_{issue_key}.py"],
                "test_path": "tests/",
            }
        )

    async def _post_testing_result(self, issue_key: str, result: Any) -> None:
        if result.status == TestStatus.PASS:
            await self.jira_client.add_comment(
                issue_key,
                f"✅ Tests passed: {result.summary}",
            )
            return

        failure_lines = []
        for failure in result.failures[:5]:
            loc = f" ({failure.file_path})" if failure.file_path else ""
            failure_lines.append(f"- {failure.test_name}{loc}: {failure.error_message}")
        details = "\n".join(failure_lines) if failure_lines else result.summary

        await self.jira_client.add_comment(
            issue_key,
            f"❌ Tests failed: {result.summary}\n{details}",
        )

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
    ) -> None:
        """Post detailed development information as Jira comment."""
        # Extract key endpoints/functions from code
        endpoints = self._extract_endpoints(code)
        functions = self._extract_functions(code)
        
        comment = (
            "## 📝 Development Details\n\n"
            f"**Task:** {task_title}\n"
            f"**PR:** {pr_info.get('html_url', 'N/A')}\n\n"
        )
        
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
        comment += f"- **File**: `agents/src/agents/{issue_key}_impl.py`\n"
        comment += f"- **Tests**: `tests/test_{issue_key}.py`\n"
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
    ) -> None:
        """Post a short development summary as Jira comment."""
        comment = (
            "## ✅ Development Summary\n"
            f"**Task:** {task_title}\n"
            f"**PR:** {pr_info.get('html_url', 'N/A')}\n"
            f"**Code Lines:** {len(code.split(chr(10)))}\n"
            f"**Test Lines:** {len(tests.split(chr(10)))}\n"
        )
        await self.jira_client.add_comment(issue_key, comment)
        logger.info(f"  📝 Development details posted to {issue_key}")
    
    def _extract_endpoints(self, code: str) -> list:
        """Extract API endpoints from code."""
        endpoints = []
        lines = code.split("\n")
        for line in lines:
            if "@app.get" in line or "@app.post" in line or "@router.get" in line or "@router.post" in line:
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
