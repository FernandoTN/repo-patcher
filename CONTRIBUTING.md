# Contributing Guide

Welcome! This repo builds an AI agent that fixes failing tests and opens guarded PRs. Please follow these guidelines to keep changes safe, minimal, and observable. See `CLAUDE.md` for the full project plan and `AGENTS.md` for agent rules.

## Workflow Expectations

- Open PRs only when all tests pass
- Prefer minimal, targeted diffs that preserve behavior
- Avoid edits to CI/secrets/infra files (see blocked paths)
- Include rationale, validation steps, and logs/metrics where relevant

## Guardrails (MVP)

- Blocked paths/patterns: `.github/`, `.git/`, `Dockerfile`, `docker-compose.yml`, `*.env`, `*.key`, `*.pem`, `*secret*`, `*config*`
- Diff limits: ≤100 lines per file, ≤500 lines total
- Iteration limit: ≤3 repair attempts per issue
- Time budget: ≤10 minutes per issue
- Large diffs (>50 lines) require human approval; infra/CI changes auto‑escalate

## Local Development

```bash
# Run tests
python -m pytest tests/ -v

# Lint
ruff check . && black --check .

# Build Docker image
docker build -t repo-patcher:latest .

# Run evaluation harness
python scripts/evaluate.py --scenarios scenarios/
```

## Commit Guidelines

- Do NOT mention AI, automation, or tools in commit messages
- Use clear, focused messages, e.g.:
  - "Add state machine implementation for test fixing"
  - "Implement patch generation with AST analysis"
  - "Fix test framework detection logic"

## Target Scope (MVP)

- Language: Python
- Tests: `pytest` unit tests (no integration/e2e for MVP)
- Repos: small–medium (≤10k LOC)

## CI/Automation Trigger (Preview)

GitHub Action runs when the `fix-me` label is applied to issues or PRs (see `CLAUDE.md` for the example workflow).

