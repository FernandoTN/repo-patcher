# Codex Agent Rules for Repo Patcher

This document gives Codex persistent, repo-specific guidance. Treat it as the governing instruction set when working in this repository. Use it together with the detailed context in `CLAUDE.md` (source of truth for scope and requirements).

## Objective

- Build an AI agent that automatically fixes failing tests in GitHub repositories and creates a guarded PR only when all tests pass, making minimal, safe changes.

## Priorities

- Correctness and safety over speed
- Minimal diffs that preserve functionality
- Full observability (tracing + metrics)
- Reproducible behavior via state machine and limits

## Scope and Non‑Goals (MVP)

- Start with Python repositories using `pytest`
- Focus on unit tests (no integration/e2e initially)
- Target small–medium OSS repos (≤10k LOC)
- Avoid edits to CI/secrets/infrastructure files

Non‑goals (for now): multi-language repairs beyond basic pytest MVP, integration tests, infra/CI authoring or refactors not needed to pass tests.

## Guardrails

- Blocked paths/patterns:
  - `.github/`, `.git/`, `Dockerfile`, `docker-compose.yml`, `*.env`, `*.key`, `*.pem`, `*secret*`, `*config*`
- Diff limits: ≤100 lines per file, ≤500 lines total
- Iteration limit: ≤3 repair attempts
- Time budget: ≤10 minutes per issue
- Memory budget: ≤2GB container
- Approval gates: large diffs (>50 lines) need approval; infra/CI changes auto‑escalate; repeated test timeouts/failures after 3 tries → escalate
- Rollback: if tests get worse or constraints violated, revert and try a minimal alternative within limits

## Operating Model (State Machine)

Execute the following phases with strict transitions and artifacts:

1) INGEST: Clone/retrieve repo, detect framework (`pytest` MVP), identify failing tests
2) PLAN: Propose minimal, test-focused changes; respect guardrails and limits
3) PATCH: Apply diffs atomically; keep changes surgical and scoped
4) TEST: Run tests with timeouts; collect logs and artifacts
5) REPAIR: Up to 3 iterations; adjust patch only where tests indicate; never broaden scope unnecessarily
6) PR: Only open when all tests pass; attach logs/diff summary; include rationale

Core internal tools (conceptual API):
- `run_tests(framework, path)`
- `search_code(query, file_types)`
- `apply_patch(diff, validate=True)` with rollback
- `open_pr(title, body, branch, files)`

## PR Policy

- Open PR only when ALL tests pass
- Keep diffs minimal and localized to failing areas
- Never modify CI/secrets/infra files; if required, escalate
- Include: summary of failures, root cause, changes made, validation steps, and metrics snapshot

## Observability and Metrics

- Emit OpenTelemetry spans for state transitions and key operations
- Structured logs with correlation IDs and error stacks
- Track metrics (names are guidance):
  - `repo_patcher_attempts_total{status="success|failure|timeout"}`
  - `repo_patcher_duration_seconds{phase="ingest|plan|patch|test|repair"}`
  - `repo_patcher_diff_lines{type="added|removed|modified"}`
  - `repo_patcher_cost_dollars{model="gpt-4o|gpt-4o-mini"}`

## Local Commands (for validation)

Use these to validate changes locally when applicable:

```bash
# Run tests
python -m pytest tests/ -v

# Lint
ruff check . && black --check .

# Build container
docker build -t repo-patcher:latest .

# Run evaluation harness
python scripts/evaluate.py --scenarios scenarios/

# Deploy to staging
./scripts/deploy.sh staging
```

## Commit Guidelines

- Do not mention AI/automation in commits
- Prefer clear, scoped messages (e.g., "Fix test framework detection logic")

## Startup Reading Order for Codex

When a new session starts, first read:
1) `AGENTS.md` (this file) for rules and constraints
2) `CLAUDE.md` for detailed scope, architecture, and evaluation criteria
3) `CONTRIBUTING.md` for local commands and commit rules

## Source of Truth

- If any guidance here seems to conflict with `CLAUDE.md`, treat `CLAUDE.md` as the detailed source of truth and this file as the agent’s concise operating manual.

