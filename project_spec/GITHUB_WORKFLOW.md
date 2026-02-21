GitHub Workflow — document-service

This document is binding for document-service.

It defines repository workflow discipline.

The goal is predictability, auditability, and low review friction.

1. Branching Model

Default branch: main

No direct pushes to main

All changes require Pull Request

Required checks must pass before merge

Admin bypass disabled

Branch naming:

feature/<short-description>

fix/<short-description>

chore/<short-description>

refactor/<short-description>

docs/<short-description>

Examples:

feature/add-version-check

fix/rollback-on-integrity-error

docs/update-failure-matrix

Rules:

No long-lived feature branches.

Branches deleted after merge.

No rebasing after review begins unless necessary.

No force pushes to shared branches.

2. Commit Format

Commits must be structured and atomic.

Format:

type: concise description

Allowed types:

feat

fix

refactor

docs

chore

test

freeze

refreeze

Examples:

feat: add optimistic concurrency check

fix: correct version increment bug

refactor: isolate domain transition logic

docs: finalize failure matrix

chore: pin dependency versions

freeze: specification v1.0 locked

Rules:

One logical change per commit.

No “misc changes”.

No mixing refactor and feature in one commit.

Freeze commit must be separate and clearly identifiable.

No large, unreviewable commits.

If a commit cannot be described concisely, it is too large.

3. Pull Request Rules

Each PR must:

Reference the relevant SPEC_PACK section(s).

Explain what changed.

Explain why.

Confirm tests updated (if behavior changed).

Confirm no scope expansion (or explicitly state expansion + spec update).

Confirm no dependency additions (or justify in TRADEOFFS.md).

PR description must answer:

What changed?

Why was this necessary?

What failure modes are impacted?

Does this alter the complexity budget?

Does this require re-freeze?

If the answer to (4) or (5) is “yes”, FREEZE.md must be updated.

No PR without explanation.

4. CI Requirements

CI must enforce:

Formatting (black)

Linting (ruff)

Type checking (mypy)

Tests (pytest)

Coverage threshold (80–85%)

CI must fail on:

Formatting errors

Lint errors

Type errors

Failing tests

Coverage below threshold

Migration upgrade/downgrade failure

Required checks may not be bypassed.

Branch protection must enforce:

Status checks required

PR review required

No direct push

5. Freeze Commit Protocol

When specification is frozen:

Commit message must be:

freeze: specification v1.0 locked

FREEZE.md must include:

Date

Version

Commit hash

No implementation commits may precede the freeze commit.

If specification changes later:

Commit message must be:

refreeze: specification vX.Y updated

Rules:

Freeze commit contains documentation only.

No code changes in freeze commit.

No silent edits to SPEC_PACK without corresponding refreeze.

Freeze is enforceable.

6. Reproducibility

A clean clone must allow:

make up
make migrate
make test

Without undocumented steps.

Environment setup must be deterministic:

Dependencies pinned

Docker base image pinned

Alembic migrations versioned

No hidden environment assumptions

If setup requires manual intervention, documentation is incomplete.

7. Discipline Standard

This repository is a hiring artifact.

Workflow discipline is part of the signal.

The repository must demonstrate:

Controlled change

Clear decision tracking

Traceable architectural intent

Spec-first engineering

No reactive coding

If workflow discipline erodes, the architectural signal erodes.