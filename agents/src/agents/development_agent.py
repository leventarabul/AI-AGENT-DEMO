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
from typing import Dict, Any, List


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
            
            # Convert code_changes dict to FileChange objects
            files = []
            for file_path, content in code_changes.items():
                files.append(FileChange(path=file_path, content=content))
            
            # Create commit message
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
