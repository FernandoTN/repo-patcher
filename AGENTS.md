# Codex Agent Rules for Repo Patcher

This document gives Codex persistent, repo-specific guidance. Treat it as the governing instruction set when working in this repository. Use it together with the detailed context in `README.md` and `CLAUDE.md` (source of truth for scope and requirements).

## Objective

- Build an AI agent that automatically fixes failing tests in GitHub repositories and creates a guarded PR only when all tests pass, making minimal, safe changes.

## Priorities

- Correctness and safety over speed
- Minimal diffs that preserve functionality
- Full observability (tracing + metrics)
- Reproducible behavior via state machine and limits

## Environment

- Python `3.9+`, Git, Docker (for container builds)
- Code quality: `black`, `ruff`, `mypy`

## Scope and Non‑Goals (MVP)

- Start with Python repositories using `pytest`
- Focus on unit tests (no integration/e2e initially)
- Target small–medium OSS repos (≤10k LOC)
- Avoid edits to CI/secrets/infrastructure files

Non‑goals (for now): multi-language repairs beyond basic pytest MVP, integration tests, infra/CI authoring or refactors not needed to pass tests.

Project status: Phase 1A (Foundation) complete; Phase 1B (State Machine) in progress.

## Guardrails

- Blocked paths/patterns:
  - `.github/`, `.git/`, `Dockerfile`, `docker-compose.yml`, `*.env`, `*.key`, `*.pem`, `*secret*`, `*config*`
- Diff limits: ≤100 lines per file, ≤500 lines total
- Iteration limit: ≤3 repair attempts
- Time budget: ≤10 minutes per issue
- Memory budget: ≤2GB container
- Approval gates: large diffs (>50 lines) need approval; infra/CI changes auto‑escalate; repeated test timeouts/failures after 3 tries → escalate; enforce cost limits with automatic cutoffs
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

Target performance (MVP guidance):
- Success@1 ≥ 60% for simple scenarios (E001–E010)
- Success@3 ≥ 85% across all scenarios
- Average cost ≤ $0.50 per successful fix
- Average diff ≤ 20 lines per fix
- 100% compliance with guardrails

## Local Commands (for validation)

Use these to validate changes locally when applicable:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=src/repo_patcher

# Lint and format checks
ruff check src/ tests/
black --check src/ tests/

# Type checking
mypy src/

# Build container
docker build -t repo-patcher:latest .

# Run evaluation harness
python scripts/run_evaluation.py
```

## Commit Guidelines

- Use Conventional Commits style (`feat:`, `fix:`, `chore:`, etc.)
- Focus messages on the "why"; keep scope tight
- Never mention AI/automation or tooling in commit messages
- Examples: `feat: add state machine skeleton`, `fix: handle timeout in test execution`

## Startup Reading Order for Codex

When a new session starts, first read:
1) `AGENTS.md` (this file) for rules and constraints
2) `README.md` for project overview, commands, and roadmap
3) `CLAUDE.md` for detailed scope, architecture, and evaluation criteria
4) `evaluation_design.md` for the evaluation framework
5) `CONTRIBUTING.md` for workflow and commit rules

## Source of Truth

- If any guidance here seems to conflict, use this precedence: `README.md` for developer commands and status; `CLAUDE.md` for deep technical scope/architecture; `evaluation_design.md` for evaluation specifics; `AGENTS.md` remains the concise operating manual.
