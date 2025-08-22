"""Evaluation runner for testing scenarios."""
import json
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import tempfile
import shutil

from .models import (
    ScenarioMetadata, 
    TestExecution, 
    ExecutionStatus, 
    FixAttempt, 
    EvaluationResult, 
    FixResult,
    EvaluationReport
)


class EvaluationRunner:
    """Runs evaluation scenarios and measures agent performance."""

    def __init__(self, scenarios_dir: Path):
        """Initialize with scenarios directory."""
        self.scenarios_dir = Path(scenarios_dir)

    def load_scenario(self, scenario_id: str) -> ScenarioMetadata:
        """Load scenario metadata from JSON file."""
        scenario_path = self.scenarios_dir / scenario_id / "scenario.json"
        with open(scenario_path) as f:
            data = json.load(f)
        return ScenarioMetadata.from_dict(data)

    def run_tests(self, repo_path: Path, test_command: str) -> TestExecution:
        """Execute tests and return results."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                test_command.split(),
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            duration = time.time() - start_time
            
            # Parse pytest output to count passed/failed tests
            stdout_lines = result.stdout.split('\n')
            tests_passed = 0
            tests_failed = 0
            error_message = None
            
            for line in stdout_lines:
                if " passed" in line and " failed" in line:
                    # Line like "1 failed, 3 passed in 0.02s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed,":
                            tests_failed = int(parts[i-1])
                        elif part == "passed":
                            tests_passed = int(parts[i-1])
                elif " passed in " in line:
                    # Line like "4 passed in 0.01s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            tests_passed = int(parts[i-1])
                elif " failed in " in line:
                    # Line like "1 failed in 0.02s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed":
                            tests_failed = int(parts[i-1])

            # Extract error message from stderr or stdout
            if result.returncode != 0:
                if result.stderr:
                    error_message = result.stderr.strip()
                else:
                    # Look for error in stdout
                    for line in stdout_lines:
                        if "Error:" in line or "NameError:" in line or "ImportError:" in line:
                            error_message = line.strip()
                            break

            test_result = ExecutionStatus.PASSED if result.returncode == 0 else ExecutionStatus.FAILED
            
            return TestExecution(
                result=test_result,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                exit_code=result.returncode,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecution(
                result=ExecutionStatus.TIMEOUT,
                stdout="",
                stderr="Test execution timed out",
                duration=duration,
                exit_code=-1,
                tests_passed=0,
                tests_failed=0,
                error_message="Timeout after 30 seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecution(
                result=ExecutionStatus.ERROR,
                stdout="",
                stderr=str(e),
                duration=duration,
                exit_code=-1,
                tests_passed=0,
                tests_failed=0,
                error_message=str(e)
            )

    def run_scenario(self, scenario_id: str, agent_runner=None) -> EvaluationResult:
        """Run a single evaluation scenario."""
        scenario = self.load_scenario(scenario_id)
        scenario_path = self.scenarios_dir / scenario_id
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "workspace"
            shutil.copytree(scenario_path / "repo", work_dir)
            
            start_time = time.time()
            attempts = []
            
            # Run initial test to confirm it fails
            initial_test = self.run_tests(work_dir, scenario.test_command)
            if initial_test.result == ExecutionStatus.PASSED:
                return EvaluationResult(
                    scenario_id=scenario_id,
                    result=FixResult.FAILURE,
                    attempts=attempts,
                    total_duration=time.time() - start_time,
                    total_cost=0.0,
                    success_at_iteration=None,
                    final_diff_size=0,
                    error_message="Scenario should start with failing tests"
                )

            # For now, if no agent is provided, just return the failure
            if agent_runner is None:
                return EvaluationResult(
                    scenario_id=scenario_id,
                    result=FixResult.FAILURE,
                    attempts=attempts,
                    total_duration=time.time() - start_time,
                    total_cost=0.0,
                    success_at_iteration=None,
                    final_diff_size=0,
                    error_message="No agent runner provided"
                )

            # TODO: Implement agent execution
            # This will be implemented when we have the state machine
            
            total_duration = time.time() - start_time
            return EvaluationResult(
                scenario_id=scenario_id,
                result=FixResult.FAILURE,
                attempts=attempts,
                total_duration=total_duration,
                total_cost=0.0,
                success_at_iteration=None,
                final_diff_size=0,
                error_message="Agent execution not implemented yet"
            )

    def list_scenarios(self) -> List[str]:
        """List all available scenarios."""
        scenarios = []
        for path in self.scenarios_dir.iterdir():
            if path.is_dir() and (path / "scenario.json").exists():
                scenarios.append(path.name)
        return sorted(scenarios)

    def run_all_scenarios(self, agent_runner=None) -> EvaluationReport:
        """Run all scenarios and generate report."""
        scenario_ids = self.list_scenarios()
        results = []
        
        for scenario_id in scenario_ids:
            print(f"Running scenario {scenario_id}...")
            result = self.run_scenario(scenario_id, agent_runner)
            results.append(result)
            print(f"  Result: {result.result.value}")

        return EvaluationReport.from_results(results)

    def generate_report(self, report: EvaluationReport) -> str:
        """Generate a formatted evaluation report."""
        lines = [
            "# Evaluation Report",
            "",
            f"**Total Scenarios**: {report.total_scenarios}",
            f"**Success@1**: {report.success_at_1_count}/{report.total_scenarios} ({report.success_at_1_count/report.total_scenarios*100:.1f}%)",
            f"**Success@3**: {report.success_at_3_count}/{report.total_scenarios} ({report.success_at_3_count/report.total_scenarios*100:.1f}%)",
            f"**Total Duration**: {report.total_duration:.2f}s",
            f"**Total Cost**: ${report.total_cost:.4f}",
            f"**Average Iterations**: {report.average_iterations:.1f}",
            f"**Average Diff Size**: {report.average_diff_size:.1f} lines",
            "",
            "## Individual Results",
            ""
        ]
        
        for result in report.results:
            status_emoji = "✅" if result.result == FixResult.SUCCESS else "❌"
            lines.extend([
                f"### {status_emoji} {result.scenario_id}",
                f"- **Result**: {result.result.value}",
                f"- **Iterations**: {result.total_iterations}",
                f"- **Duration**: {result.total_duration:.2f}s",
                f"- **Cost**: ${result.total_cost:.4f}",
                f"- **Diff Size**: {result.final_diff_size} lines",
            ])
            if result.error_message:
                lines.append(f"- **Error**: {result.error_message}")
            lines.append("")
        
        return "\n".join(lines)