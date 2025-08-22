"""Data models for evaluation framework."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path


class ExecutionStatus(Enum):
    """Test execution result."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class FixResult(Enum):
    """Fix attempt result."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class ScenarioMetadata:
    """Metadata for an evaluation scenario."""
    id: str
    name: str
    description: str
    category: str
    difficulty: str
    expected_iterations: int
    expected_diff_lines: int
    test_framework: str
    language: str
    files_to_change: List[str]
    test_command: str
    expected_error_patterns: List[str]
    learning_objectives: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioMetadata":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TestExecution:
    """Result of running tests."""
    result: ExecutionStatus
    stdout: str
    stderr: str
    duration: float
    exit_code: int
    tests_passed: int
    tests_failed: int
    error_message: Optional[str] = None


@dataclass
class FixAttempt:
    """Single fix attempt by the agent."""
    iteration: int
    diff: str
    reasoning: str
    files_changed: List[str]
    lines_added: int
    lines_removed: int
    lines_modified: int
    test_result: TestExecution
    duration: float


@dataclass
class EvaluationResult:
    """Complete evaluation result for one scenario."""
    scenario_id: str
    result: FixResult
    attempts: List[FixAttempt]
    total_duration: float
    total_cost: float
    success_at_iteration: Optional[int]
    final_diff_size: int
    error_message: Optional[str] = None

    @property
    def success_at_1(self) -> bool:
        """Check if succeeded on first attempt."""
        return self.success_at_iteration == 1

    @property
    def success_at_3(self) -> bool:
        """Check if succeeded within 3 attempts."""
        return self.success_at_iteration is not None and self.success_at_iteration <= 3

    @property
    def total_iterations(self) -> int:
        """Total number of iterations attempted."""
        return len(self.attempts)


@dataclass
class EvaluationReport:
    """Summary report for multiple scenarios."""
    results: List[EvaluationResult]
    total_scenarios: int
    success_at_1_count: int
    success_at_3_count: int
    total_duration: float
    total_cost: float
    average_iterations: float
    average_diff_size: float

    @classmethod
    def from_results(cls, results: List[EvaluationResult]) -> "EvaluationReport":
        """Generate report from evaluation results."""
        total_scenarios = len(results)
        success_at_1_count = sum(1 for r in results if r.success_at_1)
        success_at_3_count = sum(1 for r in results if r.success_at_3)
        total_duration = sum(r.total_duration for r in results)
        total_cost = sum(r.total_cost for r in results)
        
        successful_results = [r for r in results if r.result == FixResult.SUCCESS]
        average_iterations = (
            sum(r.total_iterations for r in successful_results) / len(successful_results)
            if successful_results else 0
        )
        average_diff_size = (
            sum(r.final_diff_size for r in successful_results) / len(successful_results)
            if successful_results else 0
        )

        return cls(
            results=results,
            total_scenarios=total_scenarios,
            success_at_1_count=success_at_1_count,
            success_at_3_count=success_at_3_count,
            total_duration=total_duration,
            total_cost=total_cost,
            average_iterations=average_iterations,
            average_diff_size=average_diff_size,
        )