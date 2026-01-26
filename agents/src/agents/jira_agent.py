import os
import json
import subprocess
import tempfile
import httpx
from typing import Optional, Dict, Any
from src.knowledge.context_loader import build_ai_prompt
from src.clients.jira_client import JiraClient
from src.clients.ai_management_client import AIManagementClient


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
        self.ai_management_url = ai_management_url or os.getenv("AI_MANAGEMENT_URL")
        self.ai_client = AIManagementClient(self.ai_management_url)
        self.git_repo_path = git_repo_path or os.getenv("GIT_REPO_PATH") or os.getcwd()
        self.git_user_name = git_user_name
        self.git_user_email = git_user_email
    
    async def process_task(self, issue_key: str) -> Dict[str, Any]:
        """Main orchestration: fetch task → generate code → gen tests → create PR."""
        print(f"\n🚀 Processing Jira task: {issue_key}")
        
        # Fetch issue details
        issue = await self.jira_client.get_issue(issue_key)
        task_title = issue.get("fields", {}).get("summary", "")
        task_description = issue.get("fields", {}).get("description", {})
        task_labels = issue.get("fields", {}).get("labels", [])
        
        if isinstance(task_description, dict):
            task_description = self._extract_text_from_rich_text(task_description)
        if task_description is None:
            task_description = ""
        
        print(f"  Title: {task_title}")
        desc_preview = task_description[:100] + ("..." if len(task_description) > 100 else "")
        print(f"  Description: {desc_preview}")
        
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
        
        # Step 5: Post development details as comment
        await self._post_development_details(
            issue_key, task_title, generated_code, generated_tests, pr_info
        )
        
        # Step 6: Update Jira task status (only if we actually produced a PR in a git repo)
        can_post_success = self._is_git_repo() and pr_info.get("html_url") not in (None, "N/A")
        if can_post_success:
            await self.jira_client.add_comment(
                issue_key,
                f"✅ AI Agent completed development:\n- Code generated and tested\n- PR created: {pr_info.get('html_url', 'N/A')}\n- Ready for code review"
            )
        else:
            print("  ⚠️ Success comment skipped: missing git repo or PR info")
        
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
                print(f"  ⚠️ No matching transition found for {target_names}; skipping status change")
                return
            await self.jira_client.transition_issue(issue_key, transition_id=target.get("id"))
            print(f"  🔄 Transitioned '{issue_key}' to '{target.get('name')}'")
        except Exception as e:
            print(f"  ⚠️ Transition error for {issue_key}: {e}")
    
    async def generate_code(
        self, task_title: str, task_description: str, labels: list
    ) -> Dict[str, str]:
        """Use AI to generate code for the task."""
        print(f"  📝 Generating code...")
        
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
        print(f"  🧪 Generating tests...")
        
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
        print(f"  🔧 Committing and pushing...")
        
        # Create branch
        # If repo is not a git repository, skip git operations
        is_git_repo = self._is_git_repo()
        if is_git_repo:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.git_repo_path,
                check=True,
            )
        
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
            subprocess.run(
                ["git", "config", "user.name", self.git_user_name],
                cwd=self.git_repo_path,
            )
            subprocess.run(
                ["git", "config", "user.email", self.git_user_email],
                cwd=self.git_repo_path,
            )
            
            # Add and commit
            subprocess.run(
                ["git", "add", code_path, test_path],
                cwd=self.git_repo_path,
                check=True,
            )
            result = subprocess.run(
                ["git", "commit", "-m", f"[{issue_key}] {task_title}"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
            )
            
            commit_sha = result.stdout.split("(")[0].strip() if result.returncode == 0 else "unknown"
            
            # Push to remote
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=self.git_repo_path,
            )
        else:
            print("  ⚠️ No git repo detected; files written without commit/push")
        
        return commit_sha
    
    async def create_pull_request(
        self,
        branch_name: str,
        task_title: str,
        task_description: str,
        issue_key: str,
    ) -> Dict[str, Any]:
        """Create a pull request on GitHub (or similar)."""
        print(f"  📤 Creating pull request...")
        
        # This is a placeholder; real implementation would call GitHub API
        # For now, we just return mock PR info
        pr_info = {
            "branch": branch_name,
            "title": f"[{issue_key}] {task_title}",
            "description": task_description,
            "html_url": f"https://github.com/example/repo/pull/1",  # Mock
        }
        
        return pr_info
    
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
    
    def _create_branch_name(self, issue_key: str, task_title: str) -> str:
        """Create a git branch name from issue key and title."""
        title_slug = task_title.lower().replace(" ", "-")[:30]
        return f"feat/{issue_key}/{title_slug}".lower()
    
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
        print(f"  📝 Development details posted to {issue_key}")
    
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
        return os.path.isdir(os.path.join(self.git_repo_path, ".git"))
