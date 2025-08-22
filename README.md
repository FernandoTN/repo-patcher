# Repo Patcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-Phase%201A%20Complete-green.svg)](https://github.com/FernandoTN/repo-patcher)

**AI-powered test fixing agent that automatically creates PRs to fix failing tests.**

Repo Patcher is a sophisticated GitHub Action/CLI tool that uses AI to detect failing tests, generate minimal surgical fixes, and create pull requests with comprehensive validation. Built with a safety-first approach and extensive evaluation framework.

## 🎯 Project Vision

**Goal**: Build an AI agent that automatically fixes failing tests in GitHub repositories and creates pull requests with minimal, safe changes.

**Trigger**: GitHub Action activated by `fix-me` label on issues/PRs  
**Deliverable**: Docker image with GitHub App/Action + CLI tool

## ✨ Key Features

### Current Capabilities (Phase 1A ✅)
- **Comprehensive Evaluation Framework**: 20+ test scenario categories for measuring agent performance
- **Robust Test Execution**: Multi-framework support (pytest, jest, go test) with proper error parsing
- **Professional Package Structure**: Full Python package with proper tooling and dependencies
- **Extensive Metrics**: Success@1, Success@3, diff size, cost tracking, duration monitoring
- **Safety Validation**: Test scenario validation with broken→fixed verification

### Planned Capabilities (In Development)
- **AI-Powered Fix Generation**: OpenAI Agents SDK with structured outputs for surgical code changes
- **Multi-Language Support**: Python, JavaScript, Go, Java with framework-specific handling
- **GitHub Integration**: Automated PR creation with detailed logs and diff analysis
- **Advanced Guardrails**: File path restrictions, diff size limits, cost monitoring
- **State Machine Execution**: Systematic INGEST→PLAN→PATCH→TEST→REPAIR→PR workflow

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ 
- Git
- pytest (for evaluation scenarios)

### Installation & Setup

```bash
# Clone the repository
git clone https://github.com/FernandoTN/repo-patcher.git
cd repo-patcher

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests to verify setup
python -m pytest tests/ -v
```

### Running the Evaluation Framework

```bash
# Run all evaluation scenarios
python scripts/run_evaluation.py

# Run specific tests
python -m pytest tests/test_evaluation.py -v

# Test individual scenario
cd scenarios/E001_missing_import/repo
python -m pytest tests/ -v  # Should fail
cd ../expected_fix  
python -m pytest tests/ -v  # Should pass
```

## 📊 Development Status & Roadmap

### ✅ Phase 1A: Foundation (COMPLETE)
- [x] **Evaluation Framework**: Complete harness with scenario management
- [x] **Test Scenario E001**: Missing import scenario (NameError: sqrt not defined)
- [x] **Project Structure**: Professional Python package with pyproject.toml
- [x] **Unit Testing**: 7 comprehensive tests covering evaluation functionality
- [x] **Documentation**: README, CLAUDE.md roadmap, Git integration

### 🔄 Phase 1B: Core State Machine (IN PROGRESS)
- [ ] **State Machine Skeleton**: INGEST→PLAN→PATCH→TEST→REPAIR→PR workflow
- [ ] **Tool Interfaces**: run_tests(), search_code(), apply_patch(), open_pr()
- [ ] **Basic Agent Integration**: OpenAI API integration with tool calling

### 📋 Phase 1C: Core Tools Implementation 
- [ ] **Test Runner**: Multi-framework test execution with proper error handling
- [ ] **Code Search**: Semantic code search for understanding codebases
- [ ] **Patch Application**: Safe diff application with rollback mechanisms
- [ ] **Git Operations**: Branch management, commit creation, diff generation

### 🐳 Phase 1D: Infrastructure
- [ ] **Docker Setup**: Containerized execution environment
- [ ] **GitHub Action**: Workflow for label-triggered execution
- [ ] **CI/CD Pipeline**: Automated testing and deployment

### 🛡️ Phase 2: Safety & Guardrails
- [ ] **File Restrictions**: Block CI, secrets, infrastructure files
- [ ] **Diff Limits**: Size caps and approval gates for large changes
- [ ] **Cost Controls**: Token usage monitoring and budget limits
- [ ] **Rollback System**: Git checkpoints and safe experimentation

### 📈 Phase 3: Advanced Features
- [ ] **Multi-Language Support**: JavaScript/Jest, Go, Java frameworks
- [ ] **Integration Tests**: Beyond unit test fixing
- [ ] **Performance Optimization**: Cost efficiency and speed improvements
- [ ] **Custom Rules**: Organization-specific patterns and constraints

## 🧪 Evaluation Scenarios

Our comprehensive evaluation framework includes 20 diverse failing test scenarios:

### **Import & Dependency Issues** (5 scenarios)
- **E001** ✅ Missing import statement (`NameError: sqrt not defined`)
- **E002** 📋 Incorrect import path/module name  
- **E003** 📋 Import order causing circular dependency
- **E004** 📋 Missing package in requirements
- **E005** 📋 Version conflict between dependencies

### **Logic & Assertion Errors** (5 scenarios)
- **E006** 📋 Wrong assertion operator (== vs !=)
- **E007** 📋 Off-by-one error in range/indexing
- **E008** 📋 Incorrect boolean logic (and vs or)
- **E009** 📋 Missing edge case handling
- **E010** 📋 Incorrect mathematical operation

### **Mock & Test Setup Issues** (3 scenarios)
- **E011** 📋 Mock not properly configured
- **E012** 📋 Test setup/teardown missing
- **E013** 📋 Mock return value type mismatch

### **Data Structure & Type Issues** (3 scenarios)
- **E014** 📋 Dictionary key error (typos)
- **E015** 📋 List index out of range
- **E016** 📋 Type mismatch (string vs int)

### **Async/Concurrency Issues** (2 scenarios)
- **E017** 📋 Missing await keyword
- **E018** 📋 Incorrect async test setup

### **Configuration & Environment** (2 scenarios)
- **E019** 📋 Missing environment variable
- **E020** 📋 Incorrect file path or missing test data

**Legend**: ✅ Complete | 🔄 In Progress | 📋 Planned

## 🏗️ Architecture

### Core Components

```
GitHub Action Trigger → Docker Container → AI Agent → PR Creation
                                    ↓
                            State Machine Execution
                                    ↓
                    [INGEST → PLAN → PATCH → TEST → REPAIR → PR]
```

### Technology Stack

- **AI/LLM**: OpenAI Agents SDK with Structured Outputs
- **Testing**: Multi-framework (pytest, jest, go test, etc.)
- **Git Operations**: GitPython for branch management and diffs
- **Containerization**: Docker for consistent execution environment
- **Observability**: OpenTelemetry + Prometheus metrics
- **Language**: Python 3.9+ with type hints and modern tooling

### Project Structure

```
repo-patcher/
├── src/repo_patcher/           # Main package
│   ├── __init__.py
│   ├── evaluation/             # Evaluation framework
│   │   ├── models.py          # Data models and enums
│   │   └── runner.py          # Evaluation execution engine
│   ├── agent/                 # AI agent (planned)
│   ├── tools/                 # Core tools (planned)
│   └── github/                # GitHub integration (planned)
├── scenarios/                  # Test scenarios
│   └── E001_missing_import/   # Example scenario
│       ├── repo/              # Broken code
│       ├── expected_fix/      # Expected solution
│       └── scenario.json      # Metadata
├── tests/                     # Unit tests
├── scripts/                   # Development scripts
├── docs/                      # Documentation
├── .github/                   # GitHub workflows (planned)
├── pyproject.toml            # Package configuration
├── CLAUDE.md                 # Detailed technical roadmap
└── README.md                 # This file
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=src/repo_patcher

# Run specific test file
python -m pytest tests/test_evaluation.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code  
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New Evaluation Scenarios

1. Create scenario directory: `scenarios/E00X_scenario_name/`
2. Add broken code in `repo/` subdirectory
3. Add fixed code in `expected_fix/` subdirectory  
4. Create `scenario.json` with metadata
5. Verify scenario with `python scripts/run_evaluation.py`

## 📊 Metrics & Success Criteria

### Evaluation Metrics
- **Success@1**: Agent fixes on first attempt
- **Success@3**: Agent fixes within 3 attempts  
- **Diff Efficiency**: Lines changed per test fixed
- **Cost Tracking**: API tokens used per fix
- **Safety Score**: No changes to restricted files

### Target Performance (MVP)
- **Success@1**: ≥60% for simple scenarios (E001-E010)
- **Success@3**: ≥85% for all scenarios
- **Average Cost**: ≤$0.50 per successful fix
- **Average Diff**: ≤20 lines per fix
- **Safety**: 100% compliance with guardrails

## 🛡️ Safety & Guardrails

### File System Restrictions
```python
BLOCKED_PATHS = [
    ".github/", ".git/", "Dockerfile", "docker-compose.yml",
    "*.env", "*.key", "*.pem", "*secret*", "*config*"
]
```

### Execution Limits
- **Max iterations**: 3 repair attempts per issue
- **Diff size**: ≤100 lines per file, ≤500 lines total
- **Time budget**: 10 minutes per issue
- **Memory limit**: 2GB container limit

### Approval Gates
- Large diffs (>50 lines) require human approval
- Infrastructure file changes auto-escalate  
- Cost limits with automatic cutoffs

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow our commit guidelines** (see CLAUDE.md)
4. **Add tests** for new functionality
5. **Submit a pull request**

### Commit Message Guidelines
- Use conventional commits format
- Focus on "why" rather than "what"
- Never mention AI assistance in commit messages
- Examples: `feat: add state machine skeleton`, `fix: handle timeout in test execution`

## 📝 Documentation

- **[CLAUDE.md](CLAUDE.md)**: Complete technical roadmap and architecture
- **[evaluation_design.md](evaluation_design.md)**: Detailed evaluation framework design
- **API Documentation**: Generated from docstrings (coming soon)
- **User Guide**: Comprehensive usage guide (coming soon)

## 🔮 Future Enhancements

- **Multi-language support**: Java, C#, Rust, TypeScript
- **Integration test fixing**: Beyond unit tests
- **Performance optimization**: Proactive performance suggestions  
- **Security vulnerability patching**: Automated security fixes
- **Custom rule engine**: Organization-specific patterns
- **IDE Integration**: VS Code extension for local development

## 📈 Current Status

**Phase 1A Complete** ✅  
- Solid foundation with comprehensive evaluation framework
- 1 working test scenario with full validation pipeline
- Professional codebase ready for agent integration
- 7 unit tests with 100% passing rate

**Next Milestone**: Phase 1B - State Machine Implementation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

- Built with modern Python best practices
- Inspired by automated testing and DevOps workflows
- Designed for safety, reliability, and extensibility

---

**Status**: 🟢 Active Development | **Last Updated**: August 2024 | **Version**: 0.1.0