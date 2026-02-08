"""Development agent for code generation and structured output.

Responsible for:
- Generating code based on intent context
- Returning structured output with files and commit message

IMPORTANT: This agent does NOT perform git operations.
Git operations (commit, push) are handled by GitService in the orchestrator.

Input: Structured intent context with code changes
Output: Structured result with files to create/update and commit message
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Iterable, Tuple, Optional
import re


@dataclass
class FileChange:
    """Represents a single file to be created or modified.
    
    Attributes:
        path: File path relative to repo root
        content: Full file content to write
    """
    path: str
    content: str


@dataclass
class DevelopmentResult:
    """Structured output from development agent.
    
    This output is consumed by GitService (in orchestrator layer) to perform
    actual file I/O and git operations.
    
    Attributes:
        success: Whether code generation completed successfully
        files: List of FileChange objects (path + full content)
        commit_message: Message to use for git commit
        error: Error message if success is False
    """
    success: bool
    files: List[FileChange] = field(default_factory=list)
    commit_message: str = ""
    error: str = None


class DevelopmentAgent:
    """Agent for generating code based on development intents.
    
    This agent:
    - Receives code changes from the intent context
    - Generates structured output with file contents and commit message
    - Returns immediately WITHOUT performing git operations
    
    Git operations (write files, commit, push) are handled by:
    - GitService (orchestrator/git_service.py)
    - Called by the Orchestrator after this agent completes
    """
    
    def __init__(self, repo_root: str = None):
        """Initialize development agent.
        
        Args:
            repo_root: Root directory of the Git repository
                      (unused by this agent, kept for compatibility)
        """
        # Note: repo_root is not used by DevelopmentAgent.
        # It's passed to GitService by the Orchestrator.
        self.repo_root = repo_root
    
    def execute(self, context: Dict[str, Any]) -> DevelopmentResult:
        """Generate code changes and return structured output.
        
        Args:
            context: Intent context containing:
                - jira_issue_key (str): Jira issue key
                - jira_issue_status (str): Jira issue status  
                - code_changes (dict): File path -> file content mapping
                - branch_name (str, optional): Git branch name
        
        Returns:
            DevelopmentResult with files to create/update and commit message
            
        Note:
            This method returns immediately after structuring the output.
            GitService in the orchestrator will handle actual file I/O and git operations.
        """
        try:
            # Validate input
            self._validate_context(context)
            
            # Extract parameters
            jira_key = context.get("jira_issue_key")
            code_changes = context.get("code_changes", {})
            branch_name = context.get("branch_name") or f"develop/{jira_key.lower()}"

            # Optional: auto-fix based on code review issues
            if context.get("auto_fix") and context.get("review_issues"):
                code_changes = self._apply_review_fixes(
                    code_changes=code_changes,
                    review_issues=context.get("review_issues"),
                )
            
            # Convert code_changes dict to FileChange objects
            files = []
            for file_path, content in code_changes.items():
                files.append(FileChange(path=file_path, content=content))
            
            # Create commit message
            if context.get("auto_fix"):
                commit_message = f"fix({jira_key}): address code review feedback"
            else:
                commit_message = f"feat({jira_key}): {context.get('jira_issue_status', 'Development')}"
            
            # Return structured output for GitService to process
            return DevelopmentResult(
                success=True,
                files=files,
                commit_message=commit_message,
            )
            
        except Exception as e:
            return DevelopmentResult(
                success=False,
                files=[],
                error=str(e),
            )
    
    def _validate_context(self, context: Dict[str, Any]) -> None:
        """Validate that context contains required fields.
        
        Raises:
            ValueError: If required fields are missing
        """
        required = ["jira_issue_key", "jira_issue_status", "code_changes"]
        missing = [f for f in required if f not in context]
        
        if missing:
            raise ValueError(
                f"DevelopmentAgent missing required context: {', '.join(missing)}"
            )
        
        if not isinstance(context["code_changes"], dict):
            raise ValueError("code_changes must be a dictionary (file_path -> content)")

    def _apply_review_fixes(
        self,
        code_changes: Dict[str, str],
        review_issues: Iterable[Any],
    ) -> Dict[str, str]:
        """Apply mechanical fixes based on code review issues.

        This focuses on deterministic, rule-based fixes:
        - Replace print() with logging
        - Wrap long lines
        """
        issues_by_file = self._group_issues_by_file(review_issues)
        fixed_changes: Dict[str, str] = {}

        for file_path, content in code_changes.items():
            file_issues = issues_by_file.get(file_path, [])
            updated = content

            if self._has_print_violation(file_issues):
                updated = self._replace_prints_with_logging(updated)

            updated = self._wrap_long_lines(updated, file_issues)
            fixed_changes[file_path] = updated

        return fixed_changes

    def _group_issues_by_file(self, review_issues: Iterable[Any]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for issue in review_issues or []:
            issue_dict = self._normalize_issue(issue)
            file_path = issue_dict.get("file_path")
            if not file_path:
                continue
            grouped.setdefault(file_path, []).append(issue_dict)
        return grouped

    def _normalize_issue(self, issue: Any) -> Dict[str, Any]:
        if isinstance(issue, dict):
            return issue
        issue_dict: Dict[str, Any] = {}
        for attr in ["severity", "category", "message", "line_number", "file_path"]:
            issue_dict[attr] = getattr(issue, attr, None)
        return issue_dict

    def _has_print_violation(self, issues: List[Dict[str, Any]]) -> bool:
        for issue in issues:
            message = (issue.get("message") or "").lower()
            if "print()" in message or "print" in message and "logging" in message:
                return True
        return False

    def _replace_prints_with_logging(self, content: str) -> str:
        lines = content.split("\n")
        updated_lines = []
        replaced = False

        for line in lines:
            if re.search(r"\bprint\(", line):
                updated_lines.append(re.sub(r"\bprint\(", "logger.info(", line))
                replaced = True
            else:
                updated_lines.append(line)

        if replaced:
            updated_lines = self._ensure_logger(updated_lines)

        return "\n".join(updated_lines)

    def _ensure_logger(self, lines: List[str]) -> List[str]:
        has_logging_import = any(re.match(r"\s*import\s+logging\b", line) for line in lines)
        has_logger = any(re.match(r"\s*logger\s*=\s*logging\.getLogger\(__name__\)", line) for line in lines)

        if has_logging_import and has_logger:
            return lines

        insert_at = 0
        for idx, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from ") or line.strip().startswith("import "):
                insert_at = idx + 1
                continue
            if line.strip() == "":
                continue
            break

        updated = list(lines)
        if not has_logging_import:
            updated.insert(insert_at, "import logging")
            insert_at += 1
        if not has_logger:
            updated.insert(insert_at, "logger = logging.getLogger(__name__)")
        return updated

    def _wrap_long_lines(self, content: str, issues: List[Dict[str, Any]]) -> str:
        max_len = 100
        lines = content.split("\n")
        issue_lines = {i.get("line_number") for i in issues if i.get("category") == "standards"}
        wrapped_lines: List[str] = []

        for idx, line in enumerate(lines, 1):
            if len(line) <= max_len:
                wrapped_lines.append(line)
                continue

            if issue_lines and idx not in issue_lines:
                wrapped_lines.append(line)
                continue

            wrapped_lines.extend(self._wrap_line(line, max_len))

        return "\n".join(wrapped_lines)

    def _wrap_line(self, line: str, max_len: int) -> List[str]:
        indent = re.match(r"\s*", line).group(0)
        stripped = line.strip()

        if "logger." in stripped and ("f\"" in stripped or "f'" in stripped):
            wrapped = self._wrap_logger_fstring(line)
            if wrapped:
                return wrapped

        if "os.path.dirname(" in stripped and "=" in stripped:
            wrapped = self._wrap_os_path_chain(line, indent)
            if wrapped:
                return wrapped

        if stripped.startswith("assert "):
            return self._wrap_assert(line, indent)

        # Generic wrap: break at last space before max_len using backslash continuation
        current = stripped
        parts: List[str] = []
        while len(current) > max_len:
            split_at = current.rfind(" ", 0, max_len)
            if split_at <= 0:
                break
            parts.append(indent + current[:split_at] + " \\")
            current = current[split_at + 1 :]
        parts.append(indent + current)
        return parts

    def _wrap_assert(self, line: str, indent: str) -> List[str]:
        stripped = line.strip()
        body = stripped[len("assert "):]
        return [
            f"{indent}assert (",
            f"{indent}    {body}",
            f"{indent})",
        ]

    def _wrap_logger_fstring(self, line: str) -> List[str]:
        indent = re.match(r"\s*", line).group(0)
        call_start = line.find("(")
        call_end = line.rfind(")")
        if call_start == -1 or call_end == -1 or call_end <= call_start:
            return []

        prefix = line[: call_start + 1].rstrip()
        arg = line[call_start + 1 : call_end].strip()

        f_index = arg.find("f\"")
        quote = "\""
        if f_index == -1:
            f_index = arg.find("f'")
            quote = "'"
        if f_index == -1:
            return []

        start = f_index + 2
        end = self._find_string_end(arg, start, quote)
        if end is None:
            return []

        content = arg[start:end]
        parts = content.split("\\n")
        if len(parts) == 1:
            return []

        lines = [f"{prefix}",]
        for i, part in enumerate(parts):
            suffix = "\\n" if i < len(parts) - 1 else ""
            lines.append(f"{indent}    f{quote}{part}{suffix}{quote}")
        lines.append(f"{indent})")
        return lines

    def _find_string_end(self, text: str, start: int, quote: str) -> Optional[int]:
        escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                return i
            escaped = False
        return None

    def _wrap_os_path_chain(self, line: str, indent: str) -> List[str]:
        if "=" not in line:
            return []
        prefix, expr = line.split("=", 1)
        expr = expr.strip()
        if "os.path.dirname(" not in expr:
            return []

        prefix = prefix.rstrip()
        rest = expr.replace("os.path.dirname(", f"\n{indent}    os.path.dirname(")
        parts = rest.split("\n")
        lines = [f"{prefix} = {parts[0].strip()}"]
        for part in parts[1:]:
            lines.append(part)
        return lines
