# Repo Patcher - AI-Powered Test Fixing Agent

## Project Overview

**Goal**: Build an AI agent that automatically fixes failing tests in GitHub repositories and creates pull requests with minimal, safe changes.

**Trigger**: GitHub Action activated by `fix-me` label on issues/PRs
**Deliverable**: Docker image with GitHub App/Action + CLI tool

## Success Criteria

- ✅ **Primary**: PR created only when ALL tests pass
- ✅ **Safety**: Diff size caps, no edits to CI/secrets/infrastructure files  
- ✅ **Quality**: Minimal changes that preserve functionality
- ✅ **Observability**: Full tracing and metrics for debugging

## Technical Architecture

### Core Components

```
GitHub Action Trigger → Docker Container → AI Agent → PR Creation
                                    ↓
                            State Machine Execution
                                    ↓
                    [INGEST → PLAN → PATCH → TEST → REPAIR → PR]
```

### Tech Stack

- **AI/LLM**: OpenAI Agents SDK (Python) with Structured Outputs
- **Alternative**: Plain OpenAI API with tool calling + JSON schema validation
- **Testing**: Multi-framework support (pytest, jest, go test, etc.)
- **Git**: GitPython for branch management and diffs
- **Deployment**: Docker + GitHub Actions
- **Observability**: OpenTelemetry + Prometheus metrics

## State Machine Design

```
INGEST → PLAN → PATCH → TEST → REPAIR (≤3 iterations) → PR → DONE/ESCALATE
   ↓       ↓       ↓       ↓         ↓               ↓
 Clone   Analyze  Apply   Run      Fix if          Create
 Repo    Failing  Diffs   Tests    Failed         Guarded
         Tests                     (Rollback)        PR
```

### Core Tools

1. **`run_tests(framework, path)`** - Execute test suite with timeout
2. **`search_code(query, file_types)`** - Semantic code search  
3. **`apply_patch(diff, validate=True)`** - Apply changes with rollback
4. **`open_pr(title, body, branch, files)`** - Create PR with artifacts

## Current Status

**Phase 1D Complete & Production-Ready** ✅ (**August 2024**)  
- **Complete Infrastructure**: Docker, GitHub Actions, CI/CD, and monitoring suite
- **AI Foundation**: Complete OpenAI integration with structured outputs
- **Advanced Tools**: CodeSearchTool and PatchApplyTool fully functional  
- **Production Security**: Container hardening, secret management, access controls
- **Enterprise Monitoring**: OpenTelemetry tracing, Prometheus metrics, health checks
- **Automated Deployment**: Label-triggered GitHub Actions with comprehensive workflows
- **Scalable Architecture**: Ready for enterprise deployment with horizontal scaling
- **Documentation**: Complete deployment guides and troubleshooting resources

**Ready for Phase 2**: Advanced features and multi-language support

## Implementation Phases

### Phase 1A: Foundation ✅ COMPLETE
- [x] Create evaluation harness with 20+ failing test scenarios
- [x] Build basic state machine skeleton  
- [x] Set up project structure and professional Python package
- [x] Initial testing framework and documentation

### Phase 1B: Core State Machine ✅ COMPLETE
- [x] Complete INGEST→PLAN→PATCH→TEST→REPAIR→PR workflow
- [x] Tool interfaces and abstractions
- [x] Configuration system and context management
- [x] Safety systems with cost/time limits

### Phase 1B+: Enterprise Robustness ✅ COMPLETE
- [x] **Advanced Security**: Input validation, injection prevention, path traversal protection
- [x] **Reliability Features**: Rate limiting, circuit breaker, health monitoring
- [x] **Observability**: Structured logging, correlation IDs, metrics collection
- [x] **Quality Assurance**: 26 additional robustness tests

### Phase 1C: Complete AI Integration ✅ COMPLETE & VERIFIED
- [x] **OpenAI Client**: Full API integration with structured outputs and cost tracking
- [x] **AI-Powered Handlers**: Real AI integration across all state machine handlers
- [x] **Advanced Tools**: CodeSearchTool for repository understanding, PatchApplyTool for safe modifications
- [x] **Schema Validation**: JSON schemas for all AI responses (INGEST, PLAN, PATCH)
- [x] **Testing & Verification**: Comprehensive testing with Phase 1C validation scripts
- [x] **Code Quality**: All inheritance issues resolved, static analysis warnings fixed

### Phase 1D: Infrastructure & Deployment (✅ COMPLETE)
- [x] **Docker Environment**: Production-ready containerized environment with security
- [x] **GitHub Actions**: Complete workflow automation for label-triggered execution
- [x] **CI/CD Pipeline**: Automated testing, building, security scanning, and deployment
- [x] **OpenTelemetry**: Full monitoring integration with Prometheus and Jaeger
- [x] **Production Security**: Container hardening, secret management, resource limits
- [x] **Health Monitoring**: Kubernetes-ready health endpoints and system monitoring
- [x] **Deployment Documentation**: Comprehensive production deployment guides

### Phase 2: Advanced Features & Multi-Language Support (NEXT PRIORITY 🚀)
- [ ] **JavaScript/TypeScript Support**: Jest integration and Node.js ecosystem support
- [ ] **Go Language Support**: Go test framework and toolchain integration  
- [ ] **Advanced Safety Features**: Enhanced approval workflows and risk assessment
- [ ] **Performance Optimization**: Cost efficiency and speed improvements
- [ ] **IDE Integration**: VS Code extension and developer tools
- [ ] **Evaluation Enhancement**: Additional scenarios and OpenAI-powered grading

## Guardrails & Safety

### File System Restrictions
```python
BLOCKED_PATHS = [
    ".github/", ".git/", "Dockerfile", "docker-compose.yml",
    "*.env", "*.key", "*.pem", "*secret*", "*config*"
]
```

### Execution Limits
- **Max iterations**: 3 repair attempts
- **Diff size**: ≤ 100 lines per file, ≤ 500 lines total
- **Time budget**: 10 minutes per issue
- **Memory**: 2GB container limit

### Approval Gates
- Large diffs (>50 lines) require human approval
- Infrastructure file changes auto-escalate
- Test timeout/failure after 3 attempts → escalate

## Evaluation Framework

### Test Scenarios (MVP)
1. **Python/pytest**: Import errors, assertion failures, mock issues
2. **JavaScript/jest**: Async/await bugs, module resolution
3. **Go**: Interface mismatches, nil pointer dereferences

### Metrics to Track
- **Success@1**: First attempt success rate
- **Total success**: Success after ≤3 iterations  
- **Diff efficiency**: Lines changed / tests fixed
- **Latency**: Time from trigger to PR
- **Cost**: $ per successful fix

### Automated Grading
- OpenAI graders evaluate PR descriptions
- Code quality checks (no hardcoded values, proper error handling)
- Regression testing on fixed code

## MVP Scope

**Start with**: Python repositories using pytest
**Target repos**: Small-medium OSS projects (≤10k LOC)
**Test types**: Unit tests only (no integration/e2e initially)

## Deployment Strategy

### GitHub Action Workflow
```yaml
on:
  issues:
    types: [labeled]
  pull_request:
    types: [labeled]

jobs:
  fix-tests:
    if: contains(github.event.label.name, 'fix-me')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Repo Patcher
        run: docker run --rm -v $PWD:/workspace repo-patcher:latest
```

### Required Secrets
- `OPENAI_API_KEY`: For AI agent (required)
- `GITHUB_TOKEN`: For PR creation and repository access (required)
- `JAEGER_ENDPOINT`: For distributed tracing (optional)
- `PROMETHEUS_PORT`: For metrics collection (optional, defaults to 8000)

## Observability

### Tracing
- OpenTelemetry spans for each state transition
- Jaeger integration for distributed tracing
- Structured logging with correlation IDs
- Error tracking with stack traces

### Metrics
```
repo_patcher_fix_attempts_total{status="success|failure|timeout"}
repo_patcher_fix_successes_total
repo_patcher_duration_seconds{phase="ingest|plan|patch|test|repair"}  
repo_patcher_cost_dollars{model="gpt-4o|gpt-4o-mini"}
repo_patcher_diff_lines{type="added|removed|modified"}
repo_patcher_errors_total{error_type}
repo_patcher_rate_limited_total{api}
repo_patcher_active_sessions
repo_patcher_health_status
```

### Health Monitoring
```
http://localhost:8000/health        # Comprehensive health status
http://localhost:8000/health/live   # Kubernetes liveness probe
http://localhost:8000/health/ready  # Kubernetes readiness probe
http://localhost:8000/metrics       # Prometheus metrics endpoint
```

## Development Commands

```bash
# Run tests
python -m pytest tests/ -v

# Run linting  
ruff check . && black --check .

# Build and run with Docker
docker-compose up --build

# Run evaluation
python scripts/evaluate.py --scenarios scenarios/

# Deploy with GitHub Actions (production)
# Apply 'fix-me' label to trigger workflow

# Monitor deployment
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Git Commit Guidelines

**IMPORTANT**: When making commits to this repository, do NOT mention Claude, AI assistance, or automated tools in commit messages. All commits should appear as standard developer work.

**Good commit messages:**
- "Add state machine implementation for test fixing"
- "Implement patch generation with AST analysis"
- "Fix test framework detection logic"

**Avoid:**
- "Generated with Claude"
- "AI-assisted implementation"
- "Claude Code integration"

## Future Enhancements

- Multi-language support (Java, C#, Rust)
- Integration test fixing  
- Performance optimization suggestions
- Security vulnerability patching
- Custom rule engine for organization-specific patterns