"""Tests for evaluation framework."""
import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_patcher.evaluation.runner import EvaluationRunner
from repo_patcher.evaluation.models import ExecutionStatus, FixResult


class TestEvaluationRunner:
    """Test evaluation runner functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scenarios_dir = Path(__file__).parent.parent / "scenarios"
        self.runner = EvaluationRunner(self.scenarios_dir)

    def test_list_scenarios(self):
        """Test scenario listing."""
        scenarios = self.runner.list_scenarios()
        assert "E001_missing_import" in scenarios
        assert len(scenarios) >= 1

    def test_load_scenario(self):
        """Test scenario loading."""
        scenario = self.runner.load_scenario("E001_missing_import")
        assert scenario.id == "E001"
        assert scenario.name == "missing_import"
        assert scenario.test_command == "python -m pytest tests/ -v"
        assert scenario.expected_iterations == 1

    def test_run_tests_failing(self):
        """Test running tests on failing scenario."""
        repo_path = self.scenarios_dir / "E001_missing_import" / "repo"
        result = self.runner.run_tests(repo_path, "python -m pytest tests/ -v")
        
        assert result.result == ExecutionStatus.FAILED
        assert result.exit_code != 0
        assert result.tests_failed == 1
        assert result.tests_passed == 3
        assert "sqrt" in result.stdout or "sqrt" in result.stderr

    def test_run_tests_passing(self):
        """Test running tests on fixed scenario."""
        repo_path = self.scenarios_dir / "E001_missing_import" / "expected_fix"
        result = self.runner.run_tests(repo_path, "python -m pytest tests/ -v")
        
        assert result.result == ExecutionStatus.PASSED
        assert result.exit_code == 0
        assert result.tests_failed == 0
        assert result.tests_passed == 4

    def test_run_scenario_without_agent(self):
        """Test running scenario without agent (should fail gracefully)."""
        result = self.runner.run_scenario("E001_missing_import")
        
        assert result.result == FixResult.FAILURE
        assert result.scenario_id == "E001_missing_import"
        assert result.error_message == "No agent runner provided"
        assert len(result.attempts) == 0

    def test_run_all_scenarios(self):
        """Test running all scenarios."""
        report = self.runner.run_all_scenarios()
        
        assert report.total_scenarios >= 1
        assert report.success_at_1_count == 0  # No agent provided
        assert report.success_at_3_count == 0  # No agent provided
        assert len(report.results) == report.total_scenarios

    def test_generate_report(self):
        """Test report generation."""
        report = self.runner.run_all_scenarios()
        report_text = self.runner.generate_report(report)
        
        assert "# Evaluation Report" in report_text
        assert "Total Scenarios" in report_text
        assert "Success@1" in report_text
        assert "E001_missing_import" in report_text