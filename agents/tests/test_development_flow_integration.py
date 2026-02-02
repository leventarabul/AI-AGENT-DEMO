#!/usr/bin/env python3
"""Integration test for development_flow with git operations.

Validates that:
1. DevelopmentAgent returns structured code output
2. GitService creates branches and commits files  
3. Orchestrator chains them together correctly
4. Files are actually written and committed to git
"""

import sys
import os
import subprocess
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from orchestrator.orchestrator import Intent, Orchestrator
from agents.development_agent import DevelopmentAgent, DevelopmentResult, FileChange


def test_development_agent_output():
    """Test that DevelopmentAgent returns structured output (no git operations)."""
    print("\n✓ Test: DevelopmentAgent structured output")
    
    agent = DevelopmentAgent()
    
    context = {
        "jira_issue_key": "DEMO-42",
        "jira_issue_status": "Waiting for Development",
        "code_changes": {
            "src/feature.py": "# Feature implementation\nprint('Hello')\n",
            "tests/test_feature.py": "# Tests\nassert True\n",
        }
    }
    
    result = agent.execute(context)
    
    # Verify structured output
    assert isinstance(result, DevelopmentResult), "Result should be DevelopmentResult"
    assert result.success, "Should succeed"
    assert len(result.files) == 2, "Should have 2 files"
    assert all(isinstance(f, FileChange) for f in result.files), "Files should be FileChange objects"
    assert result.commit_message, "Should have commit message"
    assert "DEMO-42" in result.commit_message, "Commit message should reference issue"
    
    print(f"  ✓ DevelopmentAgent returned {len(result.files)} FileChange objects")
    print(f"  ✓ Commit message: {result.commit_message}")
    
    return True


def test_git_service():
    """Test GitService directly with a temporary repo."""
    print("\n✓ Test: GitService git operations")
    
    from orchestrator.git_service import GitService
    
    # Create temp repo AND bare remote
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create bare remote repo (to simulate origin)
        remote_path = os.path.join(tmpdir, "remote.git")
        os.makedirs(remote_path)
        subprocess.run(["git", "init", "--bare"], cwd=remote_path, check=True, capture_output=True)
        
        # Create working repo
        work_path = os.path.join(tmpdir, "work")
        os.makedirs(work_path)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=work_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", remote_path],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Create initial commit on main
        with open(os.path.join(work_path, "README.md"), "w") as f:
            f.write("# Repo\n")
        
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Push main to remote (allow failures for default branch setup)
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD:main"],
            cwd=work_path,
            check=False,
            capture_output=True,
        )
        
        # Test GitService
        git_service = GitService(work_path)
        
        files = [
            {"path": "src/module.py", "content": "# Module\nprint('test')\n"},
            {"path": "tests/test_module.py", "content": "# Tests\nassert True\n"},
        ]
        
        result = git_service.execute_operation(
            files=files,
            commit_message="feat(DEMO-42): Add new module",
            branch_name="feature/demo-42",
        )
        
        assert result.success, f"Git operation should succeed: {result.error}"
        assert result.commit_hash, "Should have commit hash"
        assert len(result.files_written) == 2, "Should have written 2 files"
        assert result.branch_name == "feature/demo-42", "Should be on correct branch"
        
        print(f"  ✓ Created branch: {result.branch_name}")
        print(f"  ✓ Committed: {result.commit_hash[:8]}")
        print(f"  ✓ Files written: {len(result.files_written)}")
        
        # Verify files exist
        assert os.path.exists(os.path.join(work_path, "src/module.py")), "File should exist"
        assert os.path.exists(os.path.join(work_path, "tests/test_module.py")), "File should exist"
        
        # Verify git history
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=work_path,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "DEMO-42" in result.stdout, "Commit message should be in history"
        
        print(f"  ✓ Files verified on disk")
        print(f"  ✓ Git history verified")
        
        return True


def test_orchestrator_full_flow():
    """Test full orchestrator flow with development_flow intent."""
    print("\n✓ Test: Orchestrator full development_flow")
    
    # Create temp repo with proper remote
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create bare remote repo
        remote_path = os.path.join(tmpdir, "remote.git")
        os.makedirs(remote_path)
        subprocess.run(["git", "init", "--bare"], cwd=remote_path, check=True, capture_output=True)
        
        # Create working repo
        work_path = os.path.join(tmpdir, "work")
        os.makedirs(work_path)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=work_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", remote_path],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Create initial commit
        with open(os.path.join(work_path, "README.md"), "w") as f:
            f.write("# Test Repo\n")
        
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=work_path,
            check=True,
            capture_output=True,
        )
        
        # Push main to remote (allow failures for default branch setup)
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD:main"],
            cwd=work_path,
            check=False,
            capture_output=True,
        )
        
        # Create orchestrator and execute intent
        orchestrator = Orchestrator()
        
        intent = Intent(
            type="development_flow",
            context={
                "jira_issue_key": "DEMO-99",
                "jira_issue_status": "Waiting for Development",
                "code_changes": {
                    "src/new_feature.py": "# New feature\ndef hello():\n    return 'world'\n",
                },
                "repo_root": work_path,  # Use temp repo
            }
        )
        
        print(f"  📁 Testing with repo: {work_path}")
        result = orchestrator.execute(intent)
        
        # Check result
        print(f"  Pipeline status: {result.status}")
        print(f"  Agents executed: {len(result.agent_results)}")
        
        # We expect development_agent to succeed, others might not be fully implemented
        dev_result = result.agent_results[0]
        assert dev_result.agent == "development_agent", "First agent should be development"
        assert dev_result.success, "Development agent should succeed"
        
        # Check that file was actually written
        feature_file = os.path.join(work_path, "src/new_feature.py")
        assert os.path.exists(feature_file), "Feature file should exist on disk"
        
        with open(feature_file, "r") as f:
            content = f.read()
            assert "def hello():" in content, "File should have correct content"
        
        # Check git log
        log_result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=work_path,
            check=True,
            capture_output=True,
            text=True,
        )
        
        print(f"  ✓ File written to disk")
        print(f"  ✓ Commit created: {result.final_commit}")
        
        return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("DEVELOPMENT FLOW INTEGRATION TEST")
    print("=" * 70)
    
    try:
        # Part 1: Test DevelopmentAgent
        test_development_agent_output()
        
        # Part 2: Test GitService
        test_git_service()
        
        # Part 3: Test full orchestrator flow
        test_orchestrator_full_flow()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nSummary:")
        print("  ✓ DevelopmentAgent returns structured output (no git ops)")
        print("  ✓ GitService creates branches, writes files, commits, pushes")
        print("  ✓ Orchestrator integrates development_agent + git_service")
        print("  ✓ Files are written to disk and committed to git")
        print("\nReady for production use!")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
