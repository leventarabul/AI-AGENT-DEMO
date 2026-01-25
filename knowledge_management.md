# Knowledge Management

## What the knowledge base is
- Shared, curated repository of long-lived domain facts, system behaviors, and decisions that agents rely on.
- Source of truth for business rules, architecture notes, integration contracts, and operational runbooks.
- Optimized for recall and alignment, not for transient conversation history.

## How knowledge is stored
- Stored as Markdown documents under version control to ensure review, auditability, and rollback.
- Organized by domain or capability; each file should have clear ownership and update history.
- Changes follow the normal review process (PRs, approvals, and traceable commits) to keep the corpus trustworthy.

## Knowledge vs. context
- Knowledge: durable, vetted information intended to remain valid across sessions and agents.
- Context: short-lived, situation-specific data (conversation turns, task state, ephemeral telemetry) that can change quickly.
- Agents should treat context as disposable and avoid promoting it to knowledge without human review.

## How agents use knowledge
- Load relevant Markdown sections to ground reasoning, plans, and outputs.
- Cite sources by file and section to maintain traceability and enable reviewers to verify claims.
- Prefer reading over generating: reuse existing guidance before proposing new procedures.
- When knowledge is missing or outdated, propose updates as a structured change request rather than writing directly.

## Why agents must not freely write to the knowledge base
- Unreviewed writes risk embedding errors or policy violations that propagate across agents.
- Human review preserves accountability, avoids model drift, and keeps records compliant with audit requirements.
- Controlled updates prevent circular hallucinations where agents consume their own unvetted output.
- Maintaining a clean, curated corpus improves retrieval quality and long-term maintainability.
