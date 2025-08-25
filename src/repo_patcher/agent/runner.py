"""Integration between agent and evaluation framework."""
from pathlib import Path
from typing import Optional

from ..evaluation.models import FixAttempt, EvaluationResult, FixResult, ExecutionStatus
from ..evaluation.runner import EvaluationRunner as BaseEvaluationRunner
from .state_machine import AgentStateMachine
from .models import RepositoryContext, AgentState
from ..tools.test_runner import TestRunnerTool


class AgentRunner:
    """Agent runner that integrates with evaluation framework."""
    
    def __init__(self):
        self.state_machine = AgentStateMachine()
        self.test_runner = TestRunnerTool()
    
    async def fix_scenario(self, repo_path: Path, test_command: str) -> EvaluationResult:
        """Run the agent to fix a test scenario."""
        # Create repository context
        repository = RepositoryContext(
            repo_path=repo_path,
            repo_url="",  # Mock for now
            branch="main",
            commit_sha="",  # Mock for now
            test_framework="pytest",
            test_command=test_command,
            failing_tests=["test_is_prime"]  # Mock for now
        )
        
        # Execute the state machine
        session = await self.state_machine.execute_session(repository)
        
        # Convert session to evaluation result
        attempts = []
        for i, execution in enumerate(session.executions):
            if execution.state in [AgentState.PATCH, AgentState.REPAIR]:
                # Create a fix attempt record
                attempt = FixAttempt(
                    iteration=i + 1,
                    diff="mock diff",  # TODO: Get actual diff
                    reasoning=f"Execution of {execution.state.value}",
                    files_changed=["mock_file.py"],  # TODO: Get actual files
                    lines_added=1,
                    lines_removed=0,
                    lines_modified=1,
                    test_result=None,  # TODO: Get test result
                    duration=execution.duration
                )
                attempts.append(attempt)
        
        # Determine final result
        if session.current_state == AgentState.DONE:
            result = FixResult.SUCCESS
            success_at_iteration = 1  # Mock for now
        elif session.current_state == AgentState.ESCALATED:
            result = FixResult.MAX_ITERATIONS
            success_at_iteration = None
        else:
            result = FixResult.FAILURE
            success_at_iteration = None
        
        return EvaluationResult(
            scenario_id="unknown",  # Will be set by caller
            result=result,
            attempts=attempts,
            total_duration=session.duration,
            total_cost=session.total_cost,
            success_at_iteration=success_at_iteration,
            final_diff_size=sum(a.lines_added + a.lines_removed for a in attempts),
            error_message=None if result == FixResult.SUCCESS else f"Final state: {session.current_state.value}"
        )


class AgentEvaluationRunner(BaseEvaluationRunner):
    """Evaluation runner that uses the agent to fix scenarios."""
    
    def __init__(self, scenarios_dir: Path):
        super().__init__(scenarios_dir)
        self.agent_runner = AgentRunner()
    
    async def run_scenario(self, scenario_id: str, agent_runner=None) -> EvaluationResult:
        """Run a scenario using the agent."""
        scenario = self.load_scenario(scenario_id)
        scenario_path = self.scenarios_dir / scenario_id
        
        import tempfile
        import shutil
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "workspace"
            shutil.copytree(scenario_path / "repo", work_dir)
            
            # Run initial test to confirm it fails
            initial_test = self.run_tests(work_dir, scenario.test_command)
            if initial_test.result == ExecutionStatus.PASSED:
                return EvaluationResult(
                    scenario_id=scenario_id,
                    result=FixResult.FAILURE,
                    attempts=[],
                    total_duration=0.0,
                    total_cost=0.0,
                    success_at_iteration=None,
                    final_diff_size=0,
                    error_message="Scenario should start with failing tests"
                )
            
            # Use the agent to fix the scenario
            result = await self.agent_runner.fix_scenario(work_dir, scenario.test_command)
            result.scenario_id = scenario_id
            
            return result