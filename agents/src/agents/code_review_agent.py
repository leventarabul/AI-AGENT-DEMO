import json
from typing import Dict, Any, List, Tuple
import httpx
from src.clients.ai_management_client import AIManagementClient
from src.clients.jira_client import JiraClient


class CodeReviewAgent:
    """Agent that reviews code via AI and transitions tasks based on review outcome."""
    
    def __init__(
        self,
        ai_management_url: str = None,
        jira_url: str = None,
        jira_username: str = None,
        jira_token: str = None,
    ):
        import os
        self.ai_client = AIManagementClient(ai_management_url or os.getenv("AI_MANAGEMENT_URL"))
        self.jira_client = JiraClient(
            jira_url or os.getenv("JIRA_URL"),
            jira_username or os.getenv("JIRA_USERNAME"),
            jira_token or os.getenv("JIRA_API_TOKEN"),
        )
    
    async def review_pull_request(
        self, issue_key: str, code_files: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        Review PR code and decide: approve (→ Testing) or reject (→ Development Waiting).
        
        Args:
            issue_key: Jira issue key
            code_files: List of (filename, code) tuples
        
        Returns:
            {
                "approved": bool,
                "review_summary": str,
                "issues": [list of issues found],
                "checked_items": [list of what was checked],
            }
        """
        print(f"\n📋 Code review started for {issue_key}")
        
        # If code files not provided, fetch from generated files
        if not code_files:
            import os
            try:
                code_impl_path = f"/app/agents/src/agents/{issue_key}_impl.py"
                test_path = f"/app/tests/test_{issue_key}.py"
                
                code = ""
                tests = ""
                
                if os.path.exists(code_impl_path):
                    with open(code_impl_path, "r") as f:
                        code = f.read()
                
                if os.path.exists(test_path):
                    with open(test_path, "r") as f:
                        tests = f.read()
                
                if code or tests:
                    code_files = []
                    if code:
                        code_files.append((f"{issue_key}_impl.py", code))
                    if tests:
                        code_files.append((f"test_{issue_key}.py", tests))
                    print(f"  📂 Loaded code files from disk")
            except Exception as e:
                print(f"  ⚠️ Error loading code files: {e}")
        
        # Build code context
        code_context = "\n".join([
            f"## File: {fname}\n```python\n{code}\n```"
            for fname, code in code_files
        ])
        
        # If still no code context, use generic review
        if not code_context.strip():
            print(f"  ⚠️ No code context found for {issue_key}; using generic review")
            code_context = f"Code for issue {issue_key} (files not provided)"
        
        # AI code review analysis
        review_result = await self._analyze_code(code_context)
        
        # Extract decision and details
        approved = review_result.get("approved", False)
        issues = review_result.get("issues", [])
        checked_items = review_result.get("checked_items", [])
        summary = review_result.get("summary", "")
        
        print(f"  ✅ Review complete: {'APPROVED' if approved else 'NEEDS FIXES'}")
        print(f"  Issues found: {len(issues)}")
        
        # Transition in Jira based on result
        if approved:
            await self._transition_approved(issue_key, checked_items)
        else:
            await self._transition_rejected(issue_key, issues)
        
        return {
            "approved": approved,
            "review_summary": summary,
            "issues": issues,
            "checked_items": checked_items,
        }
    
    async def _analyze_code(self, code_context: str) -> Dict[str, Any]:
        """Use AI to analyze code and provide review decision."""
        review_prompt = (
            "You are an expert code reviewer. Analyze the following code and provide:\n"
            "1. Whether it should be approved for testing (Yes/No)\n"
            "2. Quality issues found (if any)\n"
            "3. What you checked\n\n"
            "CODE TO REVIEW:\n"
            + code_context + "\n\n"
            "REVIEW CHECKLIST:\n"
            "- [ ] Code follows project patterns (async/await, FastAPI, type hints)\n"
            "- [ ] Error handling is proper\n"
            "- [ ] No hardcoded values or secrets\n"
            "- [ ] Function/class documentation present\n"
            "- [ ] No obvious security issues\n"
            "- [ ] No duplicate code\n"
            "- [ ] Tests appear comprehensive\n\n"
            "RESPONSE FORMAT (JSON):\n"
            "{\n"
            '  "approved": true/false,\n'
            '  "summary": "Brief reason for decision",\n'
            '  "checked_items": ["item1", "item2", ...],\n'
            '  "issues": ["issue1", "issue2", ...]\n'
            "}\n"
            "Output ONLY valid JSON."
        )
        
        response = await self.ai_client.generate(
            prompt=review_prompt,
            provider="openai",
            max_tokens=1500,
            temperature=0.5,  # Lower temp for more consistent review
        )
        
        text = response.get("text", "{}")
        
        # Try to extract JSON
        try:
            # Find JSON in response
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
            elif "{" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
            else:
                json_str = text
            
            result = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "approved": "no issues" in text.lower() or "approved" in text.lower(),
                "summary": text[:500],
                "checked_items": ["Code analysis attempted"],
                "issues": [] if "approved" in text.lower() else ["Parse error in review"],
            }
        
        return result
    
    async def _transition_approved(self, issue_key: str, checked_items: List[str]) -> None:
        """Transition task to Testing status and add approval comment."""
        comment = (
            "✅ **CODE REVIEW PASSED**\n\n"
            "Code review approved by AI agent. Ready for testing.\n\n"
            "**Checked items:**\n"
        )
        for item in checked_items:
            comment += f"- {item}\n"
        
        comment += (
            "\n**Next step:** Automated testing will run and results will be posted here."
        )
        
        await self.jira_client.add_comment(issue_key, comment)
        
        # Transition to Testing
        try:
            transitions = await self.jira_client.get_transitions(issue_key)
            target = None
            for name in ["Testing", "Test Ready", "In Testing"]:
                for t in transitions:
                    if t.get("name") == name:
                        target = t
                        break
                if target:
                    break
            if target:
                await self.jira_client.transition_issue(issue_key, transition_id=target.get("id"))
                print(f"  🔄 Transitioned '{issue_key}' to '{target.get('name')}'")
            else:
                print(f"  ⚠️ No Testing status found; skipping transition")
        except Exception as e:
            print(f"  ⚠️ Transition error: {e}")

    
    async def _transition_rejected(self, issue_key: str, issues: List[str]) -> None:
        """Transition task back to Development Waiting and explain issues."""
        comment = (
            "❌ **CODE REVIEW NEEDS FIXES**\n\n"
            "The following issues were found during automated code review:\n\n"
        )
        for i, issue in enumerate(issues, 1):
            comment += f"{i}. {issue}\n"
        
        comment += (
            "\n**Action required:**\n"
            "- Fix the issues listed above\n"
            "- Commit and push fixes to the same branch\n"
            "- Re-submit for code review\n"
        )
        
        await self.jira_client.add_comment(issue_key, comment)
        
        # Transition back to Development Waiting
        try:
            transitions = await self.jira_client.get_transitions(issue_key)
            target = None
            for name in ["Waiting Development", "Development Waiting", "Todo"]:
                for t in transitions:
                    if t.get("name") == name:
                        target = t
                        break
                if target:
                    break
            if target:
                await self.jira_client.transition_issue(issue_key, transition_id=target.get("id"))
                print(f"  🔄 Transitioned '{issue_key}' to '{target.get('name')}'")
            else:
                print(f"  ⚠️ No Development status found; skipping transition")
        except Exception as e:
            print(f"  ⚠️ Transition error: {e}")


class CodeQualityChecker:
    """Helper to extract and check code quality metrics."""
    
    @staticmethod
    def check_code_patterns(code: str) -> Dict[str, bool]:
        """Check if code follows project patterns."""
        checks = {
            "has_type_hints": ":" in code and "->" in code,
            "uses_async": "async def" in code or "await" in code,
            "has_docstrings": '"""' in code or "'''" in code,
            "has_error_handling": "try:" in code or "except" in code,
            "imports_organized": code.startswith("import") or code.startswith("from"),
        }
        return checks
    
    @staticmethod
    def check_security(code: str) -> List[str]:
        """Check for common security issues."""
        issues = []
        
        if "password" in code.lower() and "=" in code:
            issues.append("Potential hardcoded password/secret detected")
        
        if "eval(" in code:
            issues.append("Use of eval() is dangerous")
        
        if "exec(" in code:
            issues.append("Use of exec() is dangerous")
        
        if "__import__" in code:
            issues.append("Dynamic imports without validation")
        
        return issues
    
    @staticmethod
    def check_tests(code: str) -> Dict[str, bool]:
        """Check if test code is present and structured."""
        checks = {
            "uses_pytest": "pytest" in code or "def test_" in code,
            "has_fixtures": "@pytest.fixture" in code or "@fixture" in code,
            "has_assertions": "assert" in code,
            "has_mocks": "Mock" in code or "patch" in code or "monkeypatch" in code,
        }
        return checks
