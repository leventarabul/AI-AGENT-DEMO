"""Development agent for code file creation/update and Git operations.

Responsible for:
- Creating or updating code files
- Committing changes with clear messages
- Pushing commits to the repository

Input: Structured intent context with code changes
Output: Structured result with file paths and commit hash
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path


@dataclass
class DevelopmentResult:
    """Structured output from development agent.
    
    Attributes:
        success: Whether development completed successfully
        files_modified: List of file paths modified
        commit_hash: Git commit hash if push succeeded
        commit_message: Commit message used
        error: Error message if success is False
    """
    success: bool
    files_modified: List[str]
    commit_hash: str = None
    commit_message: str = None
    error: str = None


class DevelopmentAgent:
    """Agent for executing development workflows."""
    
    def __init__(self, repo_root: str = None):
        """Initialize development agent.
        
        Args:
            repo_root: Root directory of the Git repository
                      (default: current directory)
        """
        self.repo_root = repo_root or os.getcwd()
    
    def execute(self, context: Dict[str, Any]) -> DevelopmentResult:
        """Execute development workflow.
        
        Args:
            context: Intent context containing:
                - jira_issue_key (str): Jira issue key
                - jira_issue_status (str): Jira issue status
                - code_changes (dict): File path -> file content mapping
                - branch_name (str, optional): Git branch name
        
        Returns:
            DevelopmentResult with execution status and details
        """
        try:
            # Validate input
            self._validate_context(context)
            
            # Extract parameters
            jira_key = context.get("jira_issue_key")
            code_changes = context.get("code_changes")
            branch_name = context.get("branch_name") or f"develop/{jira_key.lower()}"
            
            # Create/update files
            files_modified = self._write_files(code_changes)
            
            # Commit and push
            commit_message = f"feat({jira_key}): {context.get('jira_issue_status')}"
            commit_hash = self._commit_and_push(files_modified, commit_message, branch_name)
            
            return DevelopmentResult(
                success=True,
                files_modified=files_modified,
                commit_hash=commit_hash,
                commit_message=commit_message,
            )
            
        except Exception as e:
            return DevelopmentResult(
                success=False,
                files_modified=[],
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
    
    def _write_files(self, code_changes: Dict[str, str]) -> List[str]:
        """Write code files to disk.
        
        Args:
            code_changes: File path -> file content mapping
        
        Returns:
            List of file paths that were written
        
        Raises:
            IOError: If file write fails
        """
        files_modified = []
        
        for file_path, content in code_changes.items():
            # Ensure path is within repo root
            full_path = os.path.join(self.repo_root, file_path)
            full_path = os.path.abspath(full_path)
            
            if not full_path.startswith(os.path.abspath(self.repo_root)):
                raise ValueError(f"File path escapes repo root: {file_path}")
            
            # Create parent directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, "w") as f:
                f.write(content)
            
            files_modified.append(file_path)
        
        return files_modified
    
    def _commit_and_push(
        self, 
        files: List[str], 
        message: str, 
        branch: str
    ) -> str:
        """Commit and push changes to Git.
        
        Args:
            files: List of file paths to commit
            message: Commit message
            branch: Branch name to push to
        
        Returns:
            Commit hash
        
        Raises:
            RuntimeError: If Git operations fail
        """
        import subprocess
        
        try:
            # Stage files
            subprocess.run(
                ["git", "add"] + files,
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            commit_hash = hash_result.stdout.strip()
            
            # Push to current branch (or specified branch)
            subprocess.run(
                ["git", "push", "origin", branch],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )
            
            return commit_hash
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Git operation failed: {e.stderr or e.stdout}"
            )
