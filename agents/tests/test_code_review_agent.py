"""Tests for hardened CodeReviewAgent."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.code_review_agent import (
    CodeReviewAgent,
    ReviewDecision,
    CodeReviewResult,
)


def test_approve_clean_code():
    """Test APPROVE decision for clean code."""
    agent = CodeReviewAgent()
    context = {
        "code_changes": {
            "module.py": """
def hello():
    import logging
    logging.info("Hello world")
    return 42
"""
        }
    }
    
    result = agent.execute(context)
    
    assert result.success
    assert result.decision == ReviewDecision.APPROVE
    assert len(result.architecture_violations) == 0
    assert len(result.standard_violations) == 0
    assert "Ready for testing" in result.reasoning
    print("✓ test_approve_clean_code passed")


def test_block_architecture_violation():
    """Test BLOCK decision for architecture violations."""
    agent = CodeReviewAgent()
    context = {
        "code_changes": {
            "module.py": """
def main():
    print("Direct print not allowed")
    data = {"path": "/app/data/file.txt"}
"""
        }
    }
    
    result = agent.execute(context)
    
    assert result.success
    assert result.decision == ReviewDecision.BLOCK
    assert len(result.architecture_violations) > 0
    assert "violates architecture rules" in result.reasoning
    print("✓ test_block_architecture_violation passed")


def test_request_changes_standards():
    """Test REQUEST_CHANGES decision for coding standards violations."""
    agent = CodeReviewAgent()
    context = {
        "code_changes": {
            "module.py": """
def process():
    try:
        x = 1
    except:
        pass
"""
        }
    }
    
    result = agent.execute(context)
    
    assert result.success
    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert len(result.standard_violations) > 0
    assert "standards violations" in result.reasoning
    print("✓ test_request_changes_standards passed")


def test_edge_case_detection():
    """Test edge case detection."""
    agent = CodeReviewAgent()
    context = {
        "code_changes": {
            "module.py": """
def get_item(items):
    return items[0]
"""
        }
    }
    
    result = agent.execute(context)
    
    assert result.success
    assert result.decision == ReviewDecision.APPROVE
    assert len(result.edge_cases) > 0
    assert "edge case" in result.reasoning.lower()
    print("✓ test_edge_case_detection passed")


def test_review_decision_structure():
    """Test CodeReviewResult structure."""
    agent = CodeReviewAgent()
    context = {
        "code_changes": {
            "module.py": "import logging\nlogging.info('test')"
        }
    }
    
    result = agent.execute(context)
    
    assert isinstance(result, CodeReviewResult)
    assert hasattr(result, 'success')
    assert hasattr(result, 'decision')
    assert hasattr(result, 'issues')
    assert hasattr(result, 'architecture_violations')
    assert hasattr(result, 'standard_violations')
    assert hasattr(result, 'edge_cases')
    assert hasattr(result, 'reasoning')
    assert hasattr(result, 'approval_notes')
    print("✓ test_review_decision_structure passed")


if __name__ == "__main__":
    test_approve_clean_code()
    test_block_architecture_violation()
    test_request_changes_standards()
    test_edge_case_detection()
    test_review_decision_structure()
    print("\n✅ All tests passed!")
