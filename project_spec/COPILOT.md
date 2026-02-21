Copilot / AI Usage Policy — document-service

This document is binding for document-service.

This repository may use AI assistance.

AI operates under constraint.

AI is an accelerator, not an architect.

1. AI May

AI assistance may:

Expand and implement modules explicitly defined in SPEC_PACK.md.

Generate domain logic that enforces defined state transitions.

Generate tests derived from FAILURE_MODES.md.

Implement optimistic concurrency behavior exactly as specified.

Implement idempotency behavior exactly as specified.

Suggest refactors that do not alter architecture.

Improve formatting and readability.

Generate migration scaffolding aligned with declared schema.

Generate CI configuration consistent with BACKEND_STACK_PROFILE.md.

Improve log structure without altering semantics.

AI may only operate inside frozen boundaries.

2. AI May Not

AI may not:

Expand scope beyond SPEC_PACK.md.

Introduce new endpoints.

Add new entities.

Modify the state model.

Modify transaction boundaries.

Modify the concurrency model.

Modify the idempotency policy.

Introduce new dependencies without updating CONSTRAINTS.md.

Add background processes.

Introduce implicit retry behavior.

Introduce implicit commits.

Add caching.

Add authentication.

Introduce convenience abstractions not defined in spec.

Modify the error envelope contract.

Weaken failure handling discipline.

Add “future extensibility” scaffolding.

If it is not in the spec, it is not allowed.

3. AI Guardrails

Before accepting AI-generated code, verify:

It aligns with SPEC_PACK.md.

It respects CONSTRAINTS.md.

It follows CONVENTIONS.md.

No new dependencies were introduced.

No implicit transaction behavior was added.

No silent error handling exists.

Error envelope shape is preserved.

No layer boundary violations exist.

Dependency direction remains valid.

Tests cover new behavior.

Failure matrix scenarios remain intact.

If ambiguity is discovered:

Stop.
Update the spec.
Re-freeze if required.

No silent interpretation changes.

4. Architectural Ownership

The engineer remains responsible for:

Architectural integrity

Correct state transition modeling

Failure modeling completeness

Concurrency safety

Idempotency guarantees

Transaction boundaries

Operational correctness

Complexity budget adherence

Freeze discipline

AI does not own architectural decisions.

AI does not define invariants.

AI does not determine concurrency semantics.

AI does not decide error contracts.

AI implements what has already been decided.

5. Review Standard for AI Code

AI-generated code must pass the same standards as human-written code:

Clear naming

Explicit transaction boundaries

Deterministic error mapping

No hidden behavior

No speculative abstractions

No TODO placeholders

Full test coverage alignment

CI passes without modification

If AI introduces cleverness, reduce it.

If AI introduces abstraction layers beyond 3, reject it.

If AI writes code that obscures behavior, rewrite it.

Clarity > novelty.

6. Freeze Alignment Rule

If AI suggests:

New architectural pattern

New dependency

Change to failure behavior

Change to concurrency model

Change to state machine

The correct response is:

Do not implement.
Update SPEC_PACK.md.
Update TRADEOFFS.md.
Refreeze.
Then proceed.

Freeze is authoritative.

This repository is judged on:

Constraint discipline

Deterministic behavior

Correctness under concurrency

Failure awareness

Operational realism

AI may assist.

It may not decide.