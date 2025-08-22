# Evaluation Harness Design

## Overview
Create 15-20 failing test scenarios that progressively test the agent's capabilities, from simple fixes to more complex issues.

## Test Scenario Categories

### 1. Import & Dependency Issues (5 scenarios)
- **E001**: Missing import statement
- **E002**: Incorrect import path/module name
- **E003**: Import order causing circular dependency
- **E004**: Missing package installation in requirements
- **E005**: Version conflict between dependencies

### 2. Logic & Assertion Errors (5 scenarios)
- **E006**: Wrong assertion operator (== vs !=)
- **E007**: Off-by-one error in range/indexing
- **E008**: Incorrect boolean logic (and vs or)
- **E009**: Missing edge case handling (empty list, None values)
- **E010**: Incorrect mathematical operation

### 3. Mock & Test Setup Issues (3 scenarios)
- **E011**: Mock not properly configured/patched
- **E012**: Test setup/teardown missing
- **E013**: Mock return value doesn't match expected type

### 4. Data Structure & Type Issues (3 scenarios)
- **E014**: Dictionary key error (typo in key name)
- **E015**: List index out of range
- **E016**: Type mismatch (string vs int, list vs dict)

### 5. Async/Concurrency Issues (2 scenarios)
- **E017**: Missing await keyword
- **E018**: Incorrect async test setup

### 6. Configuration & Environment (2 scenarios)
- **E019**: Missing environment variable or config
- **E020**: Incorrect file path or missing test data file

## Scenario Structure

Each scenario will have:
```
scenarios/
├── E001_missing_import/
│   ├── repo/                    # Broken code
│   │   ├── src/calculator.py
│   │   └── tests/test_calculator.py
│   ├── expected_fix/            # Expected solution
│   │   ├── src/calculator.py
│   │   └── tests/test_calculator.py
│   ├── scenario.json           # Metadata
│   └── README.md              # Description
```

## Evaluation Metrics

### Success Criteria
- **Success@1**: Agent fixes on first attempt
- **Success@3**: Agent fixes within 3 attempts
- **Minimal Change**: Solution uses ≤ expected diff size
- **Test Pass**: All tests pass after fix
- **No Regression**: No new test failures introduced

### Measurements
- **Diff Size**: Lines added/removed/modified
- **Iteration Count**: Number of repair attempts
- **Time to Fix**: Total execution time
- **Cost**: API tokens used
- **Safety**: No changes to blocked files

### Quality Scores (OpenAI Grader)
- **Explanation Quality**: Does commit message explain the fix?
- **Code Quality**: Clean, readable solution?
- **Minimal Impact**: Surgical changes vs broad rewrites?

## Test Runner Design

```python
class EvaluationRunner:
    def run_scenario(self, scenario_id: str) -> EvaluationResult
    def run_all_scenarios(self) -> EvaluationReport
    def generate_report(self, results: List[EvaluationResult]) -> str
```

## Implementation Priority

**Phase 1A**: Create 5 basic scenarios (E001-E005)
**Phase 1B**: Implement evaluation runner
**Phase 1C**: Add remaining scenarios (E006-E020)
**Phase 1D**: Add OpenAI grading system