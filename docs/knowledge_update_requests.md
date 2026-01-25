# Knowledge Update Requests

## Purpose

This document describes how agents and engineers propose updates to the knowledge base without direct write access.

## Why This Mechanism Exists

The knowledge base is a shared, authoritative source of truth maintained under version control. Agents cannot write directly to it because:
- Unreviewed writes risk embedding errors across the system
- Human review ensures quality, accuracy, and policy compliance
- Audit trails are preserved for accountability and rollback
- This prevents agent hallucinations from becoming persistent facts

## How to Request a Knowledge Update

### For Agents

**Workflow:**
1. Identify missing or outdated knowledge during reasoning or execution
2. Create a structured knowledge update request (see template below)
3. Log the request to an audit trail or issue tracking system
4. Do **not** modify knowledge files directly
5. Wait for human review and approval before assuming the update is accepted

**Request Template:**

```
## Knowledge Update Request

**Category:** [Architecture | Integration | Rules | Runbook | Other]

**Issue:** 
Brief description of what knowledge is missing or incorrect.

**Current State:**
- Where is this documented now (if at all)?
- What does it currently say?

**Proposed Knowledge:**
Clear, accurate statement of what should be documented.

**Evidence:**
- What triggered this request?
- Where is this information coming from?
- Can this be verified?

**Impact:**
- Will other agents be affected?
- Does this require coordinated updates elsewhere?
```

### For Engineers

**Process:**
1. Review the knowledge update request
2. Verify accuracy and completeness
3. Check for cross-domain dependencies
4. Create a pull request to update knowledge_management.md or related files
5. Include reference to the original request in the commit message
6. Merge after code review approval
7. Notify agents that the knowledge has been updated

## Request Channels

**Recommended:**
- GitHub Issues (tagged `knowledge-update`)
- Team communication (Slack/email) for urgent updates
- Comments in pull requests if the need is discovered during review

**Do Not:**
- Add comments or pseudo-updates to knowledge files
- Use commit messages as a substitute for documented knowledge
- Ask agents to infer updates from conversation history

## Examples

### Good Request

```
Category: Integration

Issue: 
Demo Domain API does not currently document expected error responses for duplicate event registration.

Current State:
Not documented. Agents have to infer behavior from observation.

Proposed Knowledge:
Add section to API_EXAMPLES.md documenting:
- 409 Conflict response format when event already registered
- Retry strategy with exponential backoff
- Which field uniquely identifies an event (transaction_id + merchant_id)

Evidence:
Observed in API testing. Demo Domain API returns 409 with body:
  {"error": "event_already_processed", "transaction_id": "..."}
```

### Bad Request

```
"Update the knowledge base to say the API is faster now"
(Too vague, no evidence, no specifics)
```

## Review SLA

- **Routine updates:** 1–2 business days
- **Critical operational issues:** 4–8 hours
- **Corrections to documentation errors:** 24 hours

## Who Can Approve

- **Documentation owners** (listed in knowledge file headers)
- **Team leads** for architecture and integration changes
- **Service maintainers** for service-specific updates

## Escalation

If a knowledge update is blocked or delayed:
1. Post in team communication channels
2. Link to the original request
3. Explain the operational impact
4. If critical, escalate to tech lead or engineering manager

## Feedback to Agents

Once a knowledge update is merged:
1. Log the completion in the audit trail
2. Include the commit hash and knowledge file location
3. Agents can then safely assume the knowledge is current
4. Reference the update in future reasoning when relevant

## Maintaining Knowledge Quality

Engineers should periodically:
- Review old update requests for patterns (what's frequently asked?)
- Update documentation to be more predictive of common questions
- Add examples and clarifications based on agent feedback
- Mark outdated sections for removal or consolidation
