#!/usr/bin/env python3
"""Sanity checks for the orchestrator and development pipeline."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from orchestrator.orchestrator import Intent, Orchestrator
from orchestrator.decision_router import list_available_intents


def test_intent_creation():
    """Test that intents can be created."""
    print("✓ Test: Intent creation")
    
    intent = Intent(
        type="register_event",
        context={
            "event_code": "purchase",
            "customer_id": "cust_123",
            "transaction_id": "txn_001",
            "merchant_id": "merch_001",
            "amount": 99.99,
        }
    )
    
    assert intent.type == "register_event"
    assert intent.context["event_code"] == "purchase"
    print("  ✓ Intent creation works")


def test_routing():
    """Test that routing works."""
    print("✓ Test: Intent routing")
    
    orchestrator = Orchestrator()
    
    intent = Intent(
        type="development_flow",
        context={
            "jira_issue_key": "PROJ-123",
            "jira_issue_status": "Waiting for Development",
            "code_changes": {
                "test_file.py": "# Test code\nprint('Hello')\n"
            }
        }
    )
    
    decision = orchestrator.route(intent)
    
    assert decision.status == "success"
    assert decision.agents == ["development_agent", "code_review_agent", "testing_agent"]
    print("  ✓ development_flow routed to correct agents")


def test_available_intents():
    """Test that all intents are registered."""
    print("✓ Test: Available intents")
    
    intents = list_available_intents()
    
    expected = {
        "register_event",
        "create_campaign",
        "analyze_earnings",
        "review_code",
        "run_tests",
        "development_flow",
    }
    
    assert set(intents) >= expected
    print(f"  ✓ Found {len(intents)} intents: {', '.join(sorted(intents))}")


def test_development_flow_routing():
    """Test development_flow intent specifically."""
    print("✓ Test: development_flow execution plan")
    
    orchestrator = Orchestrator()
    
    intent = Intent(
        type="development_flow",
        context={
            "jira_issue_key": "PROJ-456",
            "jira_issue_status": "Waiting for Development",
            "code_changes": {
                "example.py": "# Code\npass\n"
            }
        }
    )
    
    decision = orchestrator.route(intent)
    
    # Verify execution plan
    assert len(decision.execution_plan.tasks) == 3
    assert decision.execution_plan.tasks[0].agent == "development_agent"
    assert decision.execution_plan.tasks[1].agent == "code_review_agent"
    assert decision.execution_plan.tasks[2].agent == "testing_agent"
    
    print("  ✓ development_flow execution plan is correct")
    print(f"    Sequence: {' → '.join([t.agent for t in decision.execution_plan.tasks])}")


def main():
    """Run all sanity checks."""
    print("\n" + "="*60)
    print("ORCHESTRATOR SANITY CHECKS")
    print("="*60 + "\n")
    
    try:
        test_intent_creation()
        test_routing()
        test_available_intents()
        test_development_flow_routing()
        
        print("\n" + "="*60)
        print("✓ ALL SANITY CHECKS PASSED")
        print("="*60 + "\n")
        return 0
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"✗ SANITY CHECK FAILED: {e}")
        print("="*60 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
