"""Learning Gate: Pattern detection and knowledge proposal generation.

Analyzes execution traces to detect repeated patterns and proposes
knowledge updates WITHOUT autonomous modification.

Key principles:
- Deterministic pattern detection (no AI/LLMs)
- Explicit gate rules and thresholds
- Structured proposals only (never direct writes)
- Human-in-the-loop for knowledge updates
- Fully explainable decisions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json

from orchestrator.execution_trace import ExecutionTrace, StepStatus, PipelineStatus


class PatternType(str, Enum):
    """Type of detected pattern."""
    REPEATED_CODE_REVIEW_FAILURE = "REPEATED_CODE_REVIEW_FAILURE"
    REPEATED_TEST_FAILURE = "REPEATED_TEST_FAILURE"
    REPEATED_DEPLOYMENT_FAILURE = "REPEATED_DEPLOYMENT_FAILURE"
    COMMON_ERROR_PATTERN = "COMMON_ERROR_PATTERN"


class GateDecision(str, Enum):
    """Learning gate decision."""
    PROPOSE = "PROPOSE"  # Pattern is significant, create proposal
    REJECT = "REJECT"    # Pattern doesn't meet threshold or criteria


class KnowledgeDomain(str, Enum):
    """Knowledge domain for proposals."""
    CODE_PATTERNS = "CODE_PATTERNS"
    TEST_PATTERNS = "TEST_PATTERNS"
    ARCHITECTURE = "ARCHITECTURE"
    API_CONTRACTS = "API_CONTRACTS"
    DECISIONS = "DECISIONS"


@dataclass
class Pattern:
    """A detected pattern from execution traces."""
    pattern_type: PatternType
    agent_name: str
    error_signature: str  # Normalized error message or pattern
    occurrences: int
    first_seen: str
    last_seen: str
    trace_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.utcnow().isoformat()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now


@dataclass
class LearningProposal:
    """A proposed knowledge update based on detected patterns.
    
    This is a READ-ONLY proposal. It never writes to knowledge files.
    Human reviewers must approve and apply proposals manually.
    """
    proposal_id: str
    pattern_type: PatternType
    source_agent: str
    observed_pattern: str  # Human-readable description
    frequency: int  # Number of occurrences
    confidence_score: float  # 0.0 to 1.0
    suggested_domain: KnowledgeDomain
    proposed_action: str  # What should be added/changed
    supporting_trace_ids: List[str]
    created_at: str
    gate_decision: GateDecision
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        """Set created_at if not provided."""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proposal_id": self.proposal_id,
            "pattern_type": self.pattern_type.value,
            "source_agent": self.source_agent,
            "observed_pattern": self.observed_pattern,
            "frequency": self.frequency,
            "confidence_score": self.confidence_score,
            "suggested_domain": self.suggested_domain.value,
            "proposed_action": self.proposed_action,
            "supporting_trace_ids": self.supporting_trace_ids,
            "created_at": self.created_at,
            "gate_decision": self.gate_decision.value,
            "rejection_reason": self.rejection_reason,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class PatternDetector:
    """Detects patterns from execution traces.
    
    Uses deterministic rules to identify repeated failures
    and common error patterns.
    """
    
    def __init__(self):
        """Initialize pattern detector."""
        self._patterns: Dict[str, Pattern] = {}
    
    def analyze_trace(self, trace: ExecutionTrace) -> List[Pattern]:
        """Analyze a single trace for patterns.
        
        Args:
            trace: Execution trace to analyze
            
        Returns:
            List of detected/updated patterns
        """
        detected = []
        
        # Look for failed steps
        for step in trace.steps:
            if step.status in [StepStatus.FAIL, StepStatus.BLOCKED]:
                pattern = self._extract_pattern(trace, step)
                if pattern:
                    detected.append(pattern)
        
        return detected
    
    def _extract_pattern(self, trace: ExecutionTrace, step: Any) -> Optional[Pattern]:
        """Extract pattern from a failed step.
        
        Args:
            trace: The execution trace
            step: The failed step
            
        Returns:
            Pattern if detected, None otherwise
        """
        # Determine pattern type based on agent
        if step.agent_name == "code_review_agent":
            pattern_type = PatternType.REPEATED_CODE_REVIEW_FAILURE
        elif step.agent_name == "testing_agent":
            pattern_type = PatternType.REPEATED_TEST_FAILURE
        else:
            pattern_type = PatternType.COMMON_ERROR_PATTERN
        
        # Normalize error message to create signature
        error_sig = self._normalize_error(step.error_message or "")
        
        # Create pattern key
        pattern_key = f"{step.agent_name}::{error_sig}"
        
        # Update or create pattern
        if pattern_key in self._patterns:
            # Existing pattern - increment
            pattern = self._patterns[pattern_key]
            pattern.occurrences += 1
            pattern.last_seen = datetime.utcnow().isoformat()
            if trace.trace_id not in pattern.trace_ids:
                pattern.trace_ids.append(trace.trace_id)
        else:
            # New pattern
            pattern = Pattern(
                pattern_type=pattern_type,
                agent_name=step.agent_name,
                error_signature=error_sig,
                occurrences=1,
                first_seen=datetime.utcnow().isoformat(),
                last_seen=datetime.utcnow().isoformat(),
                trace_ids=[trace.trace_id],
            )
            self._patterns[pattern_key] = pattern
        
        return pattern
    
    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message to create stable signature.
        
        Removes variable parts (timestamps, IDs, file paths)
        to identify similar errors.
        
        Args:
            error_message: Raw error message
            
        Returns:
            Normalized error signature
        """
        import re
        
        # Normalize common patterns
        normalized = error_message
        
        # Remove file paths
        normalized = re.sub(r'/[^\s]+\.py', '<FILE>', normalized)
        
        # Remove line numbers
        normalized = re.sub(r'line \d+', 'line <N>', normalized)
        
        # Remove timestamps
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)
        
        # Remove UUIDs
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', normalized)
        
        # Remove numbers
        normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)
        
        # Truncate if too long
        if len(normalized) > 200:
            normalized = normalized[:200] + "..."
        
        return normalized.strip()
    
    def get_all_patterns(self) -> List[Pattern]:
        """Get all detected patterns.
        
        Returns:
            List of all patterns
        """
        return list(self._patterns.values())
    
    def get_pattern_by_key(self, key: str) -> Optional[Pattern]:
        """Get a specific pattern by key.
        
        Args:
            key: Pattern key (agent_name::error_signature)
            
        Returns:
            Pattern if found, None otherwise
        """
        return self._patterns.get(key)
    
    def clear(self) -> None:
        """Clear all patterns."""
        self._patterns.clear()


class LearningGate:
    """Evaluates patterns and decides whether to propose knowledge updates.
    
    Uses explicit thresholds and rules - NO autonomous learning.
    All decisions are deterministic and explainable.
    """
    
    # Gate thresholds
    MIN_OCCURRENCES = 3  # Minimum pattern occurrences to consider
    MIN_CONFIDENCE = 0.6  # Minimum confidence score to propose
    
    # Confidence weights
    FREQUENCY_WEIGHT = 0.5
    RECENCY_WEIGHT = 0.3
    SEVERITY_WEIGHT = 0.2
    
    def __init__(self):
        """Initialize learning gate."""
        pass
    
    def evaluate(self, pattern: Pattern) -> tuple[GateDecision, Optional[str]]:
        """Evaluate a pattern and decide whether to propose.
        
        Args:
            pattern: The pattern to evaluate
            
        Returns:
            Tuple of (decision, rejection_reason)
        """
        # Rule 1: Minimum occurrences
        if pattern.occurrences < self.MIN_OCCURRENCES:
            return GateDecision.REJECT, f"Insufficient occurrences ({pattern.occurrences} < {self.MIN_OCCURRENCES})"
        
        # Rule 2: Calculate confidence score
        confidence = self._calculate_confidence(pattern)
        
        # Rule 3: Check confidence threshold
        if confidence < self.MIN_CONFIDENCE:
            return GateDecision.REJECT, f"Low confidence ({confidence:.2f} < {self.MIN_CONFIDENCE})"
        
        # All rules passed - propose
        return GateDecision.PROPOSE, None
    
    def _calculate_confidence(self, pattern: Pattern) -> float:
        """Calculate confidence score for a pattern.
        
        Confidence is based on:
        - Frequency: How often the pattern occurs
        - Recency: How recent the pattern is
        - Severity: How critical the failure is
        
        Args:
            pattern: The pattern to score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Frequency score: logarithmic scale (more occurrences = higher, but diminishing returns)
        import math
        frequency_score = min(1.0, math.log(pattern.occurrences + 1) / math.log(10))
        
        # Recency score: based on last_seen timestamp
        # For now, just use 1.0 (always recent since we just saw it)
        # Could be enhanced to decay over time
        recency_score = 1.0
        
        # Severity score: based on pattern type
        severity_map = {
            PatternType.REPEATED_CODE_REVIEW_FAILURE: 0.8,
            PatternType.REPEATED_TEST_FAILURE: 0.9,
            PatternType.REPEATED_DEPLOYMENT_FAILURE: 1.0,
            PatternType.COMMON_ERROR_PATTERN: 0.6,
        }
        severity_score = severity_map.get(pattern.pattern_type, 0.5)
        
        # Weighted combination
        confidence = (
            self.FREQUENCY_WEIGHT * frequency_score +
            self.RECENCY_WEIGHT * recency_score +
            self.SEVERITY_WEIGHT * severity_score
        )
        
        return confidence
    
    def create_proposal(self, pattern: Pattern) -> LearningProposal:
        """Create a learning proposal from an approved pattern.
        
        Args:
            pattern: The pattern to create proposal from
            
        Returns:
            LearningProposal with all metadata
        """
        import uuid
        
        # Evaluate pattern
        decision, rejection_reason = self.evaluate(pattern)
        
        # Calculate confidence
        confidence = self._calculate_confidence(pattern)
        
        # Determine knowledge domain
        domain = self._suggest_domain(pattern)
        
        # Generate proposed action
        action = self._generate_action(pattern)
        
        # Create proposal
        proposal = LearningProposal(
            proposal_id=str(uuid.uuid4()),
            pattern_type=pattern.pattern_type,
            source_agent=pattern.agent_name,
            observed_pattern=self._describe_pattern(pattern),
            frequency=pattern.occurrences,
            confidence_score=confidence,
            suggested_domain=domain,
            proposed_action=action,
            supporting_trace_ids=pattern.trace_ids.copy(),
            created_at=datetime.utcnow().isoformat(),
            gate_decision=decision,
            rejection_reason=rejection_reason,
        )
        
        return proposal
    
    def _suggest_domain(self, pattern: Pattern) -> KnowledgeDomain:
        """Suggest which knowledge domain this pattern belongs to.
        
        Args:
            pattern: The pattern
            
        Returns:
            Suggested knowledge domain
        """
        if pattern.pattern_type == PatternType.REPEATED_CODE_REVIEW_FAILURE:
            return KnowledgeDomain.CODE_PATTERNS
        elif pattern.pattern_type == PatternType.REPEATED_TEST_FAILURE:
            return KnowledgeDomain.TEST_PATTERNS
        elif pattern.pattern_type == PatternType.REPEATED_DEPLOYMENT_FAILURE:
            return KnowledgeDomain.ARCHITECTURE
        else:
            return KnowledgeDomain.DECISIONS
    
    def _generate_action(self, pattern: Pattern) -> str:
        """Generate proposed action description.
        
        Args:
            pattern: The pattern
            
        Returns:
            Human-readable proposed action
        """
        if pattern.pattern_type == PatternType.REPEATED_CODE_REVIEW_FAILURE:
            return f"Add code review guideline: '{pattern.error_signature}' to CODE_PATTERNS.md"
        elif pattern.pattern_type == PatternType.REPEATED_TEST_FAILURE:
            return f"Document test pattern: '{pattern.error_signature}' in TEST_PATTERNS.md"
        else:
            return f"Document common issue: '{pattern.error_signature}'"
    
    def _describe_pattern(self, pattern: Pattern) -> str:
        """Create human-readable pattern description.
        
        Args:
            pattern: The pattern
            
        Returns:
            Human-readable description
        """
        return (
            f"{pattern.agent_name} failed {pattern.occurrences} times "
            f"with error pattern: {pattern.error_signature}"
        )


class ProposalStore:
    """Store for learning proposals.
    
    In production, this could be:
    - Database
    - File system
    - Review queue system
    """
    
    def __init__(self):
        """Initialize proposal store."""
        self._proposals: Dict[str, LearningProposal] = {}
    
    def store(self, proposal: LearningProposal) -> None:
        """Store a proposal.
        
        Args:
            proposal: The proposal to store
        """
        self._proposals[proposal.proposal_id] = proposal
    
    def get(self, proposal_id: str) -> Optional[LearningProposal]:
        """Get a proposal by ID.
        
        Args:
            proposal_id: The proposal ID
            
        Returns:
            Proposal if found, None otherwise
        """
        return self._proposals.get(proposal_id)
    
    def get_all(self) -> List[LearningProposal]:
        """Get all proposals.
        
        Returns:
            List of all proposals
        """
        return list(self._proposals.values())
    
    def get_approved(self) -> List[LearningProposal]:
        """Get all approved proposals (PROPOSE decision).
        
        Returns:
            List of approved proposals
        """
        return [p for p in self._proposals.values() if p.gate_decision == GateDecision.PROPOSE]
    
    def get_rejected(self) -> List[LearningProposal]:
        """Get all rejected proposals.
        
        Returns:
            List of rejected proposals
        """
        return [p for p in self._proposals.values() if p.gate_decision == GateDecision.REJECT]
    
    def clear(self) -> None:
        """Clear all proposals."""
        self._proposals.clear()


# Global instances
_pattern_detector = PatternDetector()
_learning_gate = LearningGate()
_proposal_store = ProposalStore()


def get_pattern_detector() -> PatternDetector:
    """Get global pattern detector instance."""
    return _pattern_detector


def get_learning_gate() -> LearningGate:
    """Get global learning gate instance."""
    return _learning_gate


def get_proposal_store() -> ProposalStore:
    """Get global proposal store instance."""
    return _proposal_store


def analyze_and_propose(trace: ExecutionTrace) -> List[LearningProposal]:
    """Convenience function: analyze trace and generate proposals.
    
    Args:
        trace: Execution trace to analyze
        
    Returns:
        List of generated proposals (approved only)
    """
    detector = get_pattern_detector()
    gate = get_learning_gate()
    store = get_proposal_store()
    
    # Detect patterns
    patterns = detector.analyze_trace(trace)
    
    # Generate proposals
    proposals = []
    for pattern in patterns:
        proposal = gate.create_proposal(pattern)
        store.store(proposal)
        
        # Only return approved proposals
        if proposal.gate_decision == GateDecision.PROPOSE:
            proposals.append(proposal)
    
    return proposals
