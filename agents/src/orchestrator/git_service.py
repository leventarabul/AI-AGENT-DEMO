"""GitService: Handles all Git operations for the orchestrator.

Responsible for:
- Creating feature branches
- Writing files to disk
- Creating git commits
- Pushing branches to remote

CRITICAL: This is the ONLY component allowed to run git commands.
Agents must NOT run git operations directly.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GitOperationResult:
    """Result of a git operation.
    
    Attributes:
        success: Whether the operation completed successfully
        commit_hash: Git commit hash if successful
        branch_name: Branch name where commit was made
        files_written: List of file paths written to disk
        error: Error message if success is False
    """
    success: bool
    commit_hash: Optional[str] = None
    branch_name: Optional[str] = None
    files_written: List[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.files_written is None:
            self.files_written = []


class GitService:
    """Service for executing all git operations.
    
    Responsibilities:
    - Create feature branches
    - Write files to disk
    - Stage and commit changes
    - Push to remote
    
    All git commands are executed via subprocess (not shell injection).
    """
    
    def __init__(self, repo_root: str):
        """Initialize GitService with a repository root.
        
        Args:
            repo_root: Absolute path to the git repository root
            
        Raises:
            ValueError: If repo_root is not a valid git repository
        """
        self.repo_root = repo_root
        self._validate_repo()
    
    def _validate_repo(self) -> None:
        """Validate that repo_root is a valid git repository.
        
        Raises:
            ValueError: If not a valid git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            raise ValueError(
                f"'{self.repo_root}' is not a valid git repository"
            )
    
    def execute_operation(
        self,
        files: List[dict],
        commit_message: str,
        branch_name: Optional[str] = None,
    ) -> GitOperationResult:
        """Execute complete git operation: create branch, write files, commit, push.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            commit_message: Message for the commit
            branch_name: Name of the branch to create and push to
                        (default: derive from first file path)
        
        Returns:
            GitOperationResult with commit hash or error
        """
        try:
            # Step 1: Derive branch name if not provided
            if not branch_name:
                branch_name = self._generate_branch_name(files)
            
            # Step 2: Create and checkout branch
            self._create_branch(branch_name)
            
            # Step 3: Write files to disk
            files_written = self._write_files(files)
            
            # Step 4: Stage and commit
            commit_hash = self._stage_and_commit(files_written, commit_message)
            
            # Step 5: Push to remote
            self._push_branch(branch_name)
            
            # Success!
            return GitOperationResult(
                success=True,
                commit_hash=commit_hash,
                branch_name=branch_name,
                files_written=files_written,
            )
            
        except Exception as e:
            # Rollback: try to checkout main/master to avoid leaving repo in bad state
            try:
                self._checkout_branch("main")
            except Exception:
                try:
                    self._checkout_branch("master")
                except Exception:
                    pass  # Silently fail rollback
            
            # Return error result
            return GitOperationResult(
                success=False,
                error=str(e),
            )
    
    def _generate_branch_name(self, files: List[dict]) -> str:
        """Generate a branch name from Jira issue key or timestamp.
        
        Args:
            files: List of file dicts
            
        Returns:
            Branch name like "feature/DEMO-42" or "feature/auto-<timestamp>"
        """
        # Try to extract Jira key from first file path or use timestamp
        import time
        timestamp = str(int(time.time()))
        return f"feature/auto-{timestamp}"
    
    def _create_branch(self, branch_name: str) -> None:
        """Create a new feature branch.
        
        Args:
            branch_name: Name of the branch to create
            
        Raises:
            RuntimeError: If branch creation fails
        """
        try:
            # Fetch latest from remote first
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.repo_root,
                check=False,  # Don't fail if fetch fails (offline?)
                capture_output=True,
            )
            
            # Create and checkout branch from main or master
            for base_branch in ["main", "master"]:
                try:
                    subprocess.run(
                        ["git", "checkout", "-b", branch_name, f"origin/{base_branch}"],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    return
                except subprocess.CalledProcessError:
                    continue
            
            # If we get here, try from local branches
            for base_branch in ["main", "master"]:
                try:
                    subprocess.run(
                        ["git", "checkout", "-b", branch_name, base_branch],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    return
                except subprocess.CalledProcessError:
                    continue
            
            raise RuntimeError(
                f"Could not create branch {branch_name}: no valid base branch found"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create branch {branch_name}: {str(e)}")
    
    def _write_files(self, files: List[dict]) -> List[str]:
        """Write files to disk.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            
        Returns:
            List of file paths written
            
        Raises:
            IOError: If file write fails
        """
        files_written = []
        
        for file_dict in files:
            file_path = file_dict.get("path")
            content = file_dict.get("content")
            
            if not file_path or content is None:
                raise ValueError(
                    f"Invalid file dict: must have 'path' and 'content'"
                )
            
            # Construct full path within repo
            full_path = os.path.join(self.repo_root, file_path)
            full_path = os.path.abspath(full_path)
            
            # Security check: ensure path is within repo
            if not full_path.startswith(os.path.abspath(self.repo_root)):
                raise ValueError(
                    f"File path escapes repository root: {file_path}"
                )
            
            # Create parent directories
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except IOError as e:
                raise IOError(f"Failed to write {file_path}: {str(e)}")
            
            files_written.append(file_path)
        
        return files_written
    
    def _stage_and_commit(self, files: List[str], message: str) -> str:
        """Stage files and create a commit.
        
        Args:
            files: List of file paths to stage
            message: Commit message
            
        Returns:
            Commit hash
            
        Raises:
            RuntimeError: If stage or commit fails
        """
        try:
            # Stage files
            subprocess.run(
                ["git", "add"] + files,
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            commit_hash = result.stdout.strip()
            
            return commit_hash
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to stage or commit: {e.stderr or e.stdout}"
            )
    
    def _push_branch(self, branch_name: str) -> None:
        """Push branch to remote origin.
        
        Args:
            branch_name: Name of the branch to push
            
        Raises:
            RuntimeError: If push fails
        """
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to push branch {branch_name}: {e.stderr or e.stdout}"
            )
    
    def _checkout_branch(self, branch_name: str) -> None:
        """Checkout a branch (used for rollback).
        
        Args:
            branch_name: Name of the branch to checkout
            
        Raises:
            RuntimeError: If checkout fails
        """
        try:
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to checkout branch {branch_name}: {e.stderr or e.stdout}"
            )


def create_git_service(repo_root: Optional[str] = None) -> GitService:
    """Factory function to create a GitService instance.
    
    Args:
        repo_root: Path to git repository (default: current working directory)
        
    Returns:
        GitService instance
    """
    if not repo_root:
        repo_root = os.getcwd()
    
    return GitService(repo_root)
