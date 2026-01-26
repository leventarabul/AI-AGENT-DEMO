# Learning Gate Implementation Report

## Overview

Successfully implemented a Learning Gate mechanism that detects patterns from execution traces and proposes knowledge updates WITHOUT autonomous learning or modification of knowledge files.

## Implementation Date

January 26, 2026

## Problem Statement

The system executes many pipelines daily, encountering repeated failures and patterns. Currently:
- No mechanism to learn from these patterns
- Same errors occur repeatedly
- Knowledge base remains static
- Human insight required for every improvement

**Goal**: Allow the system to detect patterns and propose knowledge updates while maintaining full human control over what gets added to the knowledge base.

## Core Principles

### 1. No Autonomous Learning

❌ **FORBIDDEN**:
- Automatic knowledge base writes
- Self-modifying code
- Unsupervised learning
- LLM-based pattern detection

✅ **ALLOWED**:
- Deterministic pattern detection
- Structured proposals generation
- Human-reviewed updates
- Explicit threshold-based decisions

### 2. Deterministic Behavior

All decisions are:
- Rule-based (no randomness)
- Threshold-driven (explicit values)
- Explainable (clear reasons)
- Reproducible (same input = same output)

### 3. Human-in-the-Loop

```
Traces → Pattern Detector → Learning Gate → Proposals
                                                ↓
                                          Human Review
                                                ↓
                                        Knowledge Update
```

The Learning Gate **proposes** updates, humans **approve** and **apply** them.

## Architecture

### Components

```
ExecutionTrace (input)
    ↓
PatternDetector (analyzes failures)
    ↓
Pattern (accumulated statistics)
    ↓
LearningGate (evaluates against rules)
    ↓
LearningProposal (structured output)
    ↓
ProposalStore (storage)
```

### 1. PatternDetector

**Responsibility**: Extract patterns from execution traces

**Logic**:
```python
For each failed step in trace:
    1. Normalize error message (remove timestamps, paths, IDs)
    2. Create pattern key: "agent_name::error_signature"
    3. If pattern exists: increment count
    4. If new: create pattern with count=1
```

**Normalization**:
- File paths → `<FILE>`
- Line numbers → `line <N>`
- Timestamps → `<TIMESTAMP>`
- UUIDs → `<UUID>`
- Numbers → `<NUM>`

**Example**:
```
Input:  "File /app/src/module.py line 42: NameError"
Output: "File <FILE> line <N>: NameError"
```

This allows detection of similar errors across different files/lines.

### 2. LearningGate

**Responsibility**: Evaluate patterns and decide PROPOSE or REJECT

**Thresholds**:
```python
MIN_OCCURRENCES = 3  # Minimum pattern count to consider
MIN_CONFIDENCE = 0.6  # Minimum confidence to propose
```

**Confidence Calculation**:
```python
confidence = (
    FREQUENCY_WEIGHT * frequency_score +    # 0.5 weight
    RECENCY_WEIGHT * recency_score +        # 0.3 weight
    SEVERITY_WEIGHT * severity_score        # 0.2 weight
)
```

**Frequency Score**:
- Logarithmic scale: `log(occurrences + 1) / log(10)`
- More occurrences = higher score, but diminishing returns
- 1 occurrence → 0.30, 3 → 0.60, 10 → 1.00

**Severity Score** (by pattern type):
- REPEATED_DEPLOYMENT_FAILURE: 1.0 (highest)
- REPEATED_TEST_FAILURE: 0.9
- REPEATED_CODE_REVIEW_FAILURE: 0.8
- COMMON_ERROR_PATTERN: 0.6 (lowest)

**Decision Rules**:
1. If `occurrences < MIN_OCCURRENCES` → REJECT (too few)
2. If `confidence < MIN_CONFIDENCE` → REJECT (low confidence)
3. Otherwise → PROPOSE (meets criteria)

### 3. LearningProposal

**Structure**:
```python
@dataclass
class LearningProposal:
    proposal_id: str                    # Unique ID
    pattern_type: PatternType           # Type of pattern
    source_agent: str                   # Which agent failed
    observed_pattern: str               # Human description
    frequency: int                      # Occurrence count
    confidence_score: float             # 0.0 to 1.0
    suggested_domain: KnowledgeDomain   # Where to add knowledge
    proposed_action: str                # What to add
    supporting_trace_ids: List[str]     # Evidence
    created_at: str                     # Timestamp
    gate_decision: GateDecision         # PROPOSE or REJECT
    rejection_reason: Optional[str]     # Why rejected (if any)
```

**Knowledge Domains**:
- CODE_PATTERNS: Code review guidelines
- TEST_PATTERNS: Test failure patterns
- ARCHITECTURE: System design issues
- API_CONTRACTS: API-related patterns
- DECISIONS: Project decisions

### 4. ProposalStore

**Responsibility**: Store and retrieve proposals

**Methods**:
- `store(proposal)` - Save proposal
- `get(id)` - Get by ID
- `get_all()` - Get all proposals
- `get_approved()` - Get PROPOSE decisions only
- `get_rejected()` - Get REJECT decisions only

## Pattern Types

### 1. REPEATED_CODE_REVIEW_FAILURE

**Detected when**: `code_review_agent` step fails repeatedly

**Example**:
```
Pattern: "Missing type annotations"
Occurrences: 4
Confidence: 0.81
Suggested Domain: CODE_PATTERNS
Proposed Action: Add code review guideline: 'Missing type annotations' to CODE_PATTERNS.md
```

### 2. REPEATED_TEST_FAILURE

**Detected when**: `testing_agent` step fails repeatedly

**Example**:
```
Pattern: "Test failed: test_user_login"
Occurrences: 5
Confidence: 0.87
Suggested Domain: TEST_PATTERNS
Proposed Action: Document test pattern: 'Test failed: test_user_login' in TEST_PATTERNS.md
```

### 3. REPEATED_DEPLOYMENT_FAILURE

**Detected when**: Deployment-related agents fail repeatedly

**Example**:
```
Pattern: "Docker build timeout"
Occurrences: 3
Confidence: 0.78
Suggested Domain: ARCHITECTURE
Proposed Action: Document common issue: 'Docker build timeout'
```

### 4. COMMON_ERROR_PATTERN

**Detected when**: Other agents fail with common patterns

**Example**:
```
Pattern: "Connection timeout to API"
Occurrences: 6
Confidence: 0.72
Suggested Domain: API_CONTRACTS
Proposed Action: Document common issue: 'Connection timeout to API'
```

## Usage

### Basic Usage

```python
from orchestrator.learning_gate import analyze_and_propose
from orchestrator.execution_trace import get_trace_store

# After orchestrator executes a pipeline
result = orchestrator.execute(intent)

# Retrieve trace
trace = get_trace_store().get(result.trace_id)

# Analyze and generate proposals
proposals = analyze_and_propose(trace)

# Check proposals
for proposal in proposals:
    if proposal.gate_decision == GateDecision.PROPOSE:
        print(f"NEW PROPOSAL: {proposal.observed_pattern}")
        print(f"Confidence: {proposal.confidence_score:.2f}")
        print(f"Action: {proposal.proposed_action}")
```

### Advanced Usage

```python
from orchestrator.learning_gate import (
    get_pattern_detector,
    get_learning_gate,
    get_proposal_store,
)

# Get global instances
detector = get_pattern_detector()
gate = get_learning_gate()
store = get_proposal_store()

# Analyze trace
patterns = detector.analyze_trace(trace)

# Manually evaluate each pattern
for pattern in patterns:
    decision, reason = gate.evaluate(pattern)
    
    if decision == GateDecision.PROPOSE:
        proposal = gate.create_proposal(pattern)
        store.store(proposal)
        print(f"✅ Approved: {proposal.observed_pattern}")
    else:
        print(f"❌ Rejected: {reason}")

# Get all approved proposals
approved = store.get_approved()
print(f"Total approved proposals: {len(approved)}")
```

### Reviewing Proposals

```python
from orchestrator.learning_gate import get_proposal_store
import json

# Get all approved proposals
store = get_proposal_store()
proposals = store.get_approved()

# Export to JSON for human review
for proposal in proposals:
    print(json.dumps(proposal.to_dict(), indent=2))
    print("-" * 60)
```

## Example Output

### Proposal JSON

```json
{
  "proposal_id": "a22e8b73-6ab6-4fac-ae23-b2bdd7956a6d",
  "pattern_type": "REPEATED_CODE_REVIEW_FAILURE",
  "source_agent": "code_review_agent",
  "observed_pattern": "code_review_agent failed 4 times with error pattern: Missing type annotations",
  "frequency": 4,
  "confidence_score": 0.81,
  "suggested_domain": "CODE_PATTERNS",
  "proposed_action": "Add code review guideline: 'Missing type annotations' to CODE_PATTERNS.md",
  "supporting_trace_ids": ["t1", "t2", "t3", "t4"],
  "created_at": "2026-01-26T10:15:00",
  "gate_decision": "PROPOSE",
  "rejection_reason": null
}
```

### Terminal Output

```
============================================================
LEARNING GATE TEST SUITE
============================================================

=== Test: Pattern Detection - Single Failure ===
✓ Pattern detected: REPEATED_CODE_REVIEW_FAILURE
✓ Occurrences: 1
✓ Error signature: Missing docstrings in function foo()
✅ Test passed: Single failure pattern detected

=== Test: Pattern Accumulation ===
✓ Pattern accumulated: 3 occurrences
✓ Trace IDs: ['test-0', 'test-1', 'test-2']
✅ Test passed: Pattern accumulation works

=== Test: Gate Proposes High Frequency ===
✓ Decision: PROPOSE
✓ Confidence: 0.87
✅ Test passed: High frequency proposed
```

## Testing

### Test Coverage

**File**: `agents/tests/test_learning_gate.py` (503 lines)

**Tests** (10 total):
1. ✅ Pattern detection from single failure
2. ✅ Pattern accumulation across traces
3. ✅ Error message normalization
4. ✅ Gate rejects low frequency patterns
5. ✅ Gate proposes high frequency patterns
6. ✅ Complete proposal generation
7. ✅ Proposal serialization (dict/JSON)
8. ✅ Proposal storage and retrieval
9. ✅ End-to-end integration test
10. ✅ Different patterns tracked separately

### Test Results

```
============================================================
✅ ALL LEARNING GATE TESTS PASSED (10/10)
============================================================
```

## Configuration

### Adjusting Thresholds

Edit `learning_gate.py`:

```python
class LearningGate:
    # Gate thresholds
    MIN_OCCURRENCES = 3  # Increase to require more occurrences
    MIN_CONFIDENCE = 0.6  # Increase to be more conservative
    
    # Confidence weights
    FREQUENCY_WEIGHT = 0.5  # Adjust importance of frequency
    RECENCY_WEIGHT = 0.3    # Adjust importance of recency
    SEVERITY_WEIGHT = 0.2   # Adjust importance of severity
```

### Adding Custom Pattern Types

```python
class PatternType(str, Enum):
    # Existing types...
    CUSTOM_PATTERN = "CUSTOM_PATTERN"  # Add new type

# In PatternDetector._extract_pattern():
def _extract_pattern(self, trace, step):
    if step.agent_name == "my_custom_agent":
        pattern_type = PatternType.CUSTOM_PATTERN
    # ... rest of logic
```

## Integration with Orchestrator

The Learning Gate is designed to be called AFTER pipeline execution:

```python
# In ai_server.py or webhook handler
result = orchestrator.execute(intent)

# Analyze for learning (in background)
if result.trace_id:
    background_tasks.add_task(
        analyze_trace_for_learning,
        result.trace_id
    )

async def analyze_trace_for_learning(trace_id: str):
    """Background task to analyze trace and generate proposals."""
    from orchestrator.execution_trace import get_trace_store
    from orchestrator.learning_gate import analyze_and_propose
    
    trace = get_trace_store().get(trace_id)
    if trace:
        proposals = analyze_and_propose(trace)
        
        # Log approved proposals
        for proposal in proposals:
            logger.info(f"Learning proposal: {proposal.observed_pattern}")
            # Could send to review queue, notification system, etc.
```

## Key Constraints

### ❌ NEVER Do These:

1. **Never write to knowledge files automatically**
   - Proposals are read-only suggestions
   - Humans must review and apply

2. **Never use LLMs for pattern detection**
   - All logic must be deterministic
   - No AI-based decisions

3. **Never modify existing traces**
   - Traces are read-only input
   - No feedback loops

4. **Never auto-apply proposals**
   - Proposals require human approval
   - No autonomous actions

### ✅ Always Do These:

1. **Always use explicit thresholds**
   - MIN_OCCURRENCES, MIN_CONFIDENCE
   - Clear rejection reasons

2. **Always make decisions explainable**
   - Show confidence calculation
   - Document why PROPOSE or REJECT

3. **Always preserve evidence**
   - Store trace IDs in proposals
   - Enable human verification

4. **Always keep proposals structured**
   - Use dataclasses
   - JSON-serializable

## Future Enhancements

### Phase 1: Proposal Review UI (Future)

Build web interface for:
- Viewing approved proposals
- Filtering by confidence/domain
- One-click application to knowledge base
- Batch operations

### Phase 2: Advanced Pattern Detection (Future)

Add detectors for:
- Performance degradation patterns
- Resource usage patterns
- Security-related patterns
- Cross-agent patterns

### Phase 3: Time-based Analysis (Future)

- Pattern decay (older patterns lose weight)
- Trend analysis (increasing vs decreasing)
- Seasonal patterns

### Phase 4: Multi-dimensional Confidence (Future)

Additional factors:
- User impact score
- Business criticality
- Fix complexity
- Historical fix success rate

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `agents/src/orchestrator/learning_gate.py` | 671 | Complete Learning Gate implementation |
| `agents/tests/test_learning_gate.py` | 503 | Comprehensive test suite |
| `agents/docs/LEARNING_GATE.md` | This file | Implementation documentation |

## Success Metrics

✅ **Completeness**: All requirements implemented
- ✅ Pattern detection from execution traces
- ✅ Repeated code review failure detection
- ✅ Repeated test failure detection
- ✅ Gate evaluation with thresholds
- ✅ PROPOSE/REJECT decisions
- ✅ Structured proposals with metadata
- ✅ Confidence scoring (frequency + recency + severity)
- ✅ Knowledge domain suggestions
- ✅ Deterministic logic only (no LLMs)
- ✅ No autonomous knowledge writes

✅ **Testing**: Comprehensive coverage
- ✅ 10/10 tests passing
- ✅ Pattern detection tests
- ✅ Gate decision tests
- ✅ Proposal generation tests
- ✅ Integration tests
- ✅ Edge cases covered

✅ **Documentation**: Complete and clear
- ✅ Architecture explained
- ✅ Usage examples provided
- ✅ Constraints documented
- ✅ Future enhancements outlined

## Production Readiness

**Status**: ✅ Production Ready

**Checklist**:
- [x] All tests passing (10/10)
- [x] Deterministic behavior (no randomness)
- [x] No autonomous actions (proposals only)
- [x] Human-in-the-loop design
- [x] Explainable decisions (confidence + thresholds)
- [x] Configurable thresholds
- [x] JSON serialization
- [x] No breaking changes
- [x] Comprehensive documentation

## Next Steps

### 1. Enable in Production

Add to webhook handler:
```python
@app.post("/webhooks/jira")
async def jira_webhook(request, background_tasks):
    result = orchestrator.execute(intent)
    
    # Add learning analysis
    background_tasks.add_task(
        analyze_trace_for_learning,
        result.trace_id
    )
```

### 2. Set Up Review Process

1. Create daily/weekly report of proposals
2. Assign reviewers for each knowledge domain
3. Define approval workflow
4. Track applied vs rejected proposals

### 3. Monitor Metrics

Track:
- Proposals generated per day
- Approval rate
- Time to apply proposals
- Knowledge base growth
- Reduction in repeated failures

### 4. Iterate on Thresholds

Based on production data:
- Adjust MIN_OCCURRENCES if too many/few proposals
- Tune confidence weights for better scoring
- Add domain-specific thresholds

---

**Implementation Complete**: January 26, 2026
**Status**: ✅ All requirements met, all tests passing, production ready
**Key Achievement**: Safe, deterministic learning WITHOUT autonomous modification
