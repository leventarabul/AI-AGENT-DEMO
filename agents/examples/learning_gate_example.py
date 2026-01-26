"""Example: Using Learning Gate to detect patterns and generate proposals.

This example shows how to integrate Learning Gate into your workflow.
"""

from orchestrator.orchestrator import Orchestrator, Intent
from orchestrator.learning_gate import (
    analyze_and_propose,
    get_proposal_store,
    GateDecision,
)
from orchestrator.execution_trace import get_trace_store


def simulate_repeated_failures():
    """Simulate repeated failures to trigger learning proposals."""
    
    print("\n" + "="*60)
    print("Learning Gate Example: Repeated Code Review Failures")
    print("="*60)
    
    orchestrator = Orchestrator()
    
    # Simulate 5 code reviews with same issue
    for i in range(5):
        intent = Intent(
            type="review_code",
            context={
                "repository": f"repo-{i}",
                "pull_request_url": f"https://github.com/test/repo/pull/{i}",
                "issue_key": f"DEMO-{100+i}",
            },
            metadata={"source": "jira_webhook"},
        )
        
        # Execute pipeline
        result = orchestrator.execute(intent)
        
        print(f"\n--- Execution {i+1} ---")
        print(f"Status: {result.status}")
        print(f"Trace ID: {result.trace_id}")
        
        # Analyze for patterns
        trace = get_trace_store().get(result.trace_id)
        if trace:
            proposals = analyze_and_propose(trace)
            
            if proposals:
                print(f"🔔 LEARNING PROPOSALS GENERATED: {len(proposals)}")
                for proposal in proposals:
                    print(f"\n  Proposal: {proposal.observed_pattern}")
                    print(f"  Confidence: {proposal.confidence_score:.2f}")
                    print(f"  Domain: {proposal.suggested_domain.value}")
                    print(f"  Action: {proposal.proposed_action}")
            else:
                print("  No proposals yet (below threshold)")
    
    # Show final results
    print("\n" + "="*60)
    print("Final Learning Results")
    print("="*60)
    
    store = get_proposal_store()
    approved = store.get_approved()
    rejected = store.get_rejected()
    
    print(f"\nTotal Proposals: {len(store.get_all())}")
    print(f"  Approved: {len(approved)}")
    print(f"  Rejected: {len(rejected)}")
    
    if approved:
        print("\n--- Approved Proposals for Human Review ---")
        for i, proposal in enumerate(approved, 1):
            print(f"\n{i}. {proposal.observed_pattern}")
            print(f"   Frequency: {proposal.frequency} occurrences")
            print(f"   Confidence: {proposal.confidence_score:.2f}")
            print(f"   Suggested Action:")
            print(f"   → {proposal.proposed_action}")
            print(f"   Evidence: {len(proposal.supporting_trace_ids)} traces")
    
    print("\n" + "="*60)
    print("Next Step: Human reviews and applies proposals to knowledge base")
    print("="*60 + "\n")


def export_proposals_for_review():
    """Export proposals to JSON for human review."""
    
    import json
    
    store = get_proposal_store()
    approved = store.get_approved()
    
    if not approved:
        print("No approved proposals to export")
        return
    
    print(f"\nExporting {len(approved)} proposal(s) to JSON...\n")
    
    for proposal in approved:
        # Export as JSON
        print(json.dumps(proposal.to_dict(), indent=2))
        print("-" * 60)


if __name__ == "__main__":
    simulate_repeated_failures()
    export_proposals_for_review()
