# Agent Architecture & Component Documentation

This document provides comprehensive documentation of the Repo Patcher agent architecture, components, and operational guidelines. Use it as the definitive reference for understanding how the system works.

## 🎯 **System Objective**

Build a production-ready AI agent that automatically fixes failing tests in GitHub repositories and creates pull requests with minimal, safe changes.

**Core Principle**: Safety and correctness over speed - the agent must never make destructive changes.

---

## 📋 **Current Status: Phase 1C In Progress (Robustness Complete)**

### **✅ Implemented Components**
- **Production-ready state machine** with complete INGEST→PLAN→PATCH→TEST→REPAIR→PR workflow
- **Enterprise robustness suite** with comprehensive security, reliability, and observability
  - **Security**: Input validation, sanitization, injection prevention, path traversal protection
  - **Reliability**: Rate limiting, circuit breaker, exponential backoff, health monitoring
  - **Observability**: Structured logging, correlation IDs, metrics, cost tracking
  - **Configuration**: JSON schema validation, type safety, secure defaults
  - **Operations**: Graceful shutdown, resource cleanup, system monitoring
- **Comprehensive configuration system** with environment support and validation
- **Advanced context management** with session persistence and conversation memory  
- **Professional logging framework** with structured JSON output and session tracking
- **Safety systems** with cost/time limits and automatic cutoffs
- **Complete CLI interface** with scenario management and configuration tools
- **49 comprehensive tests** (23 original + 26 robustness) with enhanced coverage and 100% robustness test success

### **🔄 Next Phase: Phase 1C - Real AI Integration**
Replace mock implementations with actual OpenAI API integration and real tool functionality on a secure, reliable foundation.

---

## 🏗️ **Architecture Overview**

### **High-Level Flow**
```
GitHub Action Trigger → Docker Container → AI Agent → PR Creation
                                    ↓
                            State Machine Execution
                                    ↓
                    [INGEST → PLAN → PATCH → TEST → REPAIR → PR]
```

### **Core Components**

#### **1. Agent State Machine** (`src/repo_patcher/agent/`)
**Purpose**: Orchestrates the complete fix workflow with proper state transitions

- **`state_machine.py`**: Core state machine with 6 handlers
- **`models.py`**: Data models for sessions, states, and execution tracking
- **`runner.py`**: Integration bridge with evaluation framework
- **`config.py`**: Configuration management with environment support
- **`context.py`**: Session persistence and conversation memory
- **`logging_config.py`**: Structured logging with JSON output
- **`exceptions.py`**: Custom exception hierarchy for error handling

#### **2. Enterprise Robustness Modules** (`src/repo_patcher/agent/`)
**Purpose**: Provides production-grade security, reliability, and observability

- **`validation.py`**: Input validation and sanitization with injection prevention
- **`rate_limiter.py`**: Rate limiting, circuit breaker, and exponential backoff
- **`structured_logging.py`**: Enhanced logging with correlation IDs and metrics
- **`config_schema.py`**: JSON schema validation for secure configuration
- **`health.py`**: Health monitoring and system resource tracking
- **`shutdown.py`**: Graceful shutdown handling and resource cleanup

#### **3. Tool Framework** (`src/repo_patcher/tools/`)
**Purpose**: Provides reusable tools for repository operations

- **`base.py`**: Abstract base class with timing, error handling, and cost tracking
- **`test_runner.py`**: Multi-framework test execution (pytest, jest, go test)
- **Future**: Code search, patch application, PR creation tools

#### **4. Evaluation System** (`src/repo_patcher/evaluation/`)
**Purpose**: Measures agent performance across diverse test scenarios

- **`models.py`**: Evaluation data models and result tracking
- **`runner.py`**: Scenario execution and report generation
- **Integration**: Seamless connection with agent state machine

#### **5. CLI Interface** (`src/repo_patcher/cli.py`)
**Purpose**: Command-line interface for all operations

- **Evaluation**: Run scenarios with or without AI agent
- **Configuration**: Generate and manage configuration files
- **Scenario Management**: Create new test scenarios
- **Interactive Demo**: Showcase agent capabilities

---

## 🔄 **State Machine Details**

### **State Handlers**

#### **1. IngestHandler** (INGEST State)
**Current**: Mock implementation  
**Phase 1C Goal**: Real repository analysis

**Responsibilities**:
- Clone/analyze repository structure and dependencies
- Run initial tests to identify failures and parse output
- Build codebase understanding (functions, classes, imports)
- Create failure categorization and impact assessment

**Input**: Repository context with path, test command, framework
**Output**: Failing tests list, error analysis, code context

#### **2. PlanHandler** (PLAN State)  
**Current**: Mock implementation
**Phase 1C Goal**: AI-powered fix strategy generation

**Responsibilities**:
- Analyze error messages and failure patterns
- Generate step-by-step fix plan with confidence scoring
- Assess risk level and validate against safety constraints
- Create iteration strategy for complex fixes

**Input**: Repository context, failing tests, error analysis
**Output**: Structured fix plan with steps, risk assessment, confidence scores

#### **3. PatchHandler** (PATCH State)
**Current**: Mock implementation  
**Phase 1C Goal**: Real code generation and modification

**Responsibilities**:
- Generate precise code changes using AI assistance
- Apply changes with AST-aware modifications for surgical precision
- Validate changes against safety rules and diff limits
- Create rollback points for failed modifications

**Input**: Fix plan, repository context, target files
**Output**: Applied patches with diffs, backup information

#### **4. TestHandler** (TEST State)
**Current**: Basic test execution
**Phase 1C Goal**: Enhanced test analysis and reporting

**Responsibilities**:
- Execute test suite with proper timeout and error handling
- Parse and categorize test results with failure analysis
- Detect regressions and validate fix effectiveness
- Generate detailed test reports for decision making

**Input**: Modified repository, test configuration
**Output**: Test results, success/failure analysis, regression detection

#### **5. RepairHandler** (REPAIR State)
**Current**: Mock implementation
**Phase 1C Goal**: Intelligent iteration logic

**Responsibilities**:
- Analyze why previous fix attempts failed
- Generate improved strategies based on failure patterns
- Learn from previous attempts within session context
- Escalate to human review when iteration limit reached

**Input**: Previous attempts, failure analysis, session history
**Output**: Repair strategy or escalation decision

#### **6. PRHandler** (PR State)
**Current**: Mock implementation
**Phase 1C Goal**: Real GitHub PR creation

**Responsibilities**:
- Generate professional PR title and description
- Create feature branch with descriptive commit messages
- Push changes and create PR with logs and artifacts
- Add labels, reviewers, and link to original issue

**Input**: Successful fixes, test results, session metadata
**Output**: Created PR with comprehensive documentation

### **State Transition Rules**

```python
IDLE → INGEST       # Start processing
INGEST → PLAN       # Repository analyzed
PLAN → PATCH        # Fix strategy created
PATCH → TEST        # Changes applied
TEST → DONE         # All tests pass ✅
TEST → REPAIR       # Tests still fail, retry needed
REPAIR → PLAN       # Generate new strategy (iteration++)
REPAIR → ESCALATED  # Max iterations reached
Any → FAILED        # Unrecoverable error
Any → ESCALATED     # Safety violation or manual review needed
```

---

## ⚙️ **Configuration System**

### **AgentConfig Class** (`config.py`)
**Purpose**: Centralized configuration with validation

```python
# Core execution limits
max_iterations: int = 3
max_session_duration: int = 600  # 10 minutes
max_cost_per_session: float = 5.0

# Safety constraints  
max_diff_lines_per_file: int = 100
max_total_diff_lines: int = 500
require_approval_threshold: int = 50

# AI model settings
model_name: str = "gpt-4"
temperature: float = 0.1
max_tokens: int = 4000
```

### **Environment Configuration**
Load settings via environment variables:
```bash
export AGENT_MAX_ITERATIONS=5
export AGENT_MAX_COST=10.0  
export AGENT_MODEL=gpt-4
export AGENT_TEMPERATURE=0.1
```

### **File-Based Configuration**
JSON configuration files for complex setups:
```json
{
  "max_iterations": 3,
  "model_name": "gpt-4",
  "blocked_paths": [".github/", "*.env"],
  "allowed_file_types": [".py", ".js", ".ts"]
}
```

---

## 🧠 **Context Management**

### **SessionContext Class** (`context.py`)
**Purpose**: Maintains state across the entire agent session

#### **Code Context**
- File structure mapping and dependency analysis
- Function signatures and class hierarchies  
- Import relationships and usage patterns
- Test patterns and framework conventions

#### **Conversation Context**
- AI conversation history with role-based messages
- System prompts and model instructions
- Previous attempts and learned patterns
- Context window management for large sessions

#### **Persistence**
- Save/load session context to JSON files
- Resume interrupted sessions with full context
- Share context between different execution phases
- Audit trail for debugging and analysis

---

## 📊 **Logging & Observability**

### **Structured Logging** (`logging_config.py`)
**Purpose**: Professional logging with session tracking and JSON output

#### **Log Levels & Formats**
- **Console**: Colored output with session IDs for development
- **File**: Structured JSON logs for production monitoring
- **Context**: Automatic session ID, state, duration, and cost tracking

#### **Log Structure**
```json
{
  "timestamp": "2024-08-25T10:30:00",
  "level": "INFO",
  "logger": "repo_patcher.agent[abc12345]",
  "message": "State PLAN completed successfully",
  "session_id": "abc12345-def6-7890",
  "state": "plan",
  "duration": 2.34,
  "cost": 0.15
}
```

#### **Session Context**
```python
with LoggingSession(session_id="abc123", state="plan"):
    logger.info("Planning fix strategy")  # Automatically includes context
```

---

## 🛡️ **Safety Systems**

### **Built-in Guardrails**
- **File restrictions**: Block CI, secrets, infrastructure files
- **Diff limits**: ≤100 lines per file, ≤500 lines total  
- **Cost limits**: Automatic cutoff at configured threshold
- **Time limits**: Session timeout with graceful termination
- **Iteration limits**: Maximum 3 repair attempts before escalation

### **Safety Validation**
```python
# Automatic safety checks in AgentSession
session.check_cost_limit()     # True if over budget
session.check_time_limit()     # True if over time
session.is_safe_to_continue()  # Overall safety check
```

### **Escalation Triggers**
- Large diffs requiring human approval (>50 lines)
- Infrastructure file modifications
- Repeated failures after max iterations
- Safety constraint violations
- Cost or time budget exceeded

---

## 🔧 **Tool Framework**

### **BaseTool Class** (`tools/base.py`)
**Purpose**: Standard interface for all agent tools

```python
class BaseTool(ABC):
    async def execute(self, **kwargs) -> ToolResult
    def _calculate_cost(self, **kwargs) -> float
    def create_call_record(self, parameters, result) -> ToolCall
```

### **Tool Features**
- **Error Handling**: Comprehensive exception catching and reporting
- **Timing**: Automatic duration measurement for performance analysis
- **Cost Tracking**: Token usage and API cost calculation
- **Result Validation**: Structured result objects with success/failure status

### **Available Tools**
1. **TestRunnerTool**: Multi-framework test execution with result parsing
2. **CodeSearchTool**: Semantic code search (placeholder for Phase 1C)
3. **PatchApplyTool**: Safe file modification (placeholder for Phase 1C)  
4. **PRCreationTool**: GitHub PR automation (placeholder for Phase 1C)

---

## 🧪 **Evaluation Framework Integration**

### **Agent Integration**
- **AgentRunner**: Bridges state machine with evaluation framework
- **AgentEvaluationRunner**: Extends base evaluation with agent execution
- **Seamless Conversion**: Automatic translation between agent sessions and evaluation results

### **Evaluation Metrics**
- **Success@1**: First attempt success rate (target: ≥60%)
- **Success@3**: Success within 3 attempts (target: ≥85%)
- **Cost Efficiency**: Average cost per fix (target: ≤$0.50)
- **Diff Efficiency**: Lines changed per fix (target: ≤20 lines)
- **Safety Compliance**: Zero safety violations (target: 100%)

---

## 💻 **CLI Operations**

### **Available Commands**
```bash
# Run evaluation with AI agent
repo-patcher evaluate scenarios/ --use-agent

# Interactive demo
repo-patcher demo scenarios/

# Configuration management
repo-patcher config --output config.json

# Create new test scenario  
repo-patcher create-scenario scenarios/ E022_test --description "Description"

# Advanced usage with custom config
repo-patcher --config config.json --log-level DEBUG evaluate scenarios/
```

---

## 📋 **Development Guidelines**

### **Code Quality Standards**
- **Testing**: Minimum 80% coverage with comprehensive test scenarios
- **Type Safety**: Full type hints with mypy strict mode
- **Formatting**: Black code formatting with ruff linting
- **Documentation**: Comprehensive docstrings and inline comments

### **Testing Strategy**
- **Unit Tests**: Individual component testing (23 current tests)
- **Integration Tests**: End-to-end workflow validation
- **Mock Testing**: Comprehensive mock implementations for development
- **Real Testing**: Actual API integration testing in Phase 1C

### **Commit Guidelines**
- **Format**: Conventional Commits (`feat:`, `fix:`, `chore:`)
- **Focus**: Emphasize "why" over "what" in commit messages
- **Scope**: Keep changes focused and atomic
- **No AI Mentions**: Never reference AI assistance in commit messages

### **Performance Guidelines**
- **Cost Monitoring**: Track all API costs with automatic limits
- **Performance Profiling**: Measure latency at each state transition
- **Resource Limits**: Enforce memory and time constraints
- **Optimization**: Prioritize accuracy over speed in MVP

---

## 🚀 **Phase 1C Implementation Priority**

### **Immediate Tasks**
1. **OpenAI Integration**: Replace mock handlers with real AI API calls
2. **Repository Analysis**: Implement actual codebase understanding
3. **Fix Generation**: Create real code changes with AI assistance
4. **Safety Testing**: Validate all guardrails with real AI output

### **Success Criteria**
- All 6 state handlers working with real AI integration
- At least 5 evaluation scenarios passing (E001-E005)
- Cost per fix under $1.00 (will optimize to $0.50 later)
- Zero safety violations in testing

---

## 📚 **Documentation Hierarchy**

1. **AGENTS.md** (this file): Architecture and component documentation
2. **README.md**: User-facing overview, installation, and usage
3. **TODO.md**: Comprehensive project roadmap with detailed tasks
4. **CLAUDE.md**: Deep technical architecture and evaluation criteria
5. **evaluation_design.md**: Evaluation framework specifications

---

**Last Updated**: August 2024 | **Phase**: 1C In Progress (Robustness Complete) | **Architecture**: Enterprise-Ready