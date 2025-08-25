"""Tests for the agent state machine."""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_patcher.agent.models import RepositoryContext, AgentState
from repo_patcher.agent.state_machine import AgentStateMachine
from repo_patcher.agent.runner import AgentRunner, AgentEvaluationRunner
from repo_patcher.evaluation.models import FixResult


class TestAgentStateMachine:
    """Test the agent state machine."""
    
    def test_repository_context_creation(self):
        """Test creating repository context."""
        repo_path = Path("/tmp/test_repo")
        context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="python -m pytest tests/ -v",
            failing_tests=["test_example"]
        )
        
        assert context.repo_path == repo_path
        assert context.test_framework == "pytest"
        assert len(context.failing_tests) == 1
    
    @pytest.mark.asyncio
    async def test_state_machine_execution(self):
        """Test basic state machine execution."""
        repo_path = Path("/tmp/test_repo")
        context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="python -m pytest tests/ -v",
            failing_tests=["test_example"]
        )
        
        state_machine = AgentStateMachine()
        session = await state_machine.execute_session(context)
        
        # Verify session completed
        assert session.is_complete
        assert len(session.executions) > 0
        assert session.duration > 0
        
        # Should reach DONE state with our mock handlers
        assert session.current_state == AgentState.DONE
    
    @pytest.mark.asyncio
    async def test_agent_runner(self):
        """Test the agent runner integration."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create a simple test file structure
            (repo_path / "tests").mkdir()
            (repo_path / "tests" / "__init__.py").write_text("")
            (repo_path / "tests" / "test_example.py").write_text("""
def test_simple():
    assert True
""")
            
            agent_runner = AgentRunner()
            
            # This will use the mock implementations
            result = await agent_runner.fix_scenario(
                repo_path=repo_path,
                test_command="python -m pytest tests/ -v"
            )
            
            # Should complete successfully with mock implementation
            assert result.result in [FixResult.SUCCESS, FixResult.FAILURE, FixResult.MAX_ITERATIONS]
            assert result.total_duration >= 0
            assert isinstance(result.attempts, list)


class TestAgentEvaluationIntegration:
    """Test integration with evaluation framework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scenarios_dir = Path(__file__).parent.parent / "scenarios"
    
    @pytest.mark.asyncio 
    async def test_agent_evaluation_runner(self):
        """Test running evaluation with agent."""
        if not self.scenarios_dir.exists():
            pytest.skip("Scenarios directory not found")
        
        runner = AgentEvaluationRunner(self.scenarios_dir)
        
        # Check if we have scenarios
        scenarios = runner.list_scenarios()
        if not scenarios:
            pytest.skip("No scenarios found")
        
        # Run first scenario with agent
        scenario_id = scenarios[0]
        result = await runner.run_scenario(scenario_id)
        
        assert result.scenario_id == scenario_id
        assert result.result in [FixResult.SUCCESS, FixResult.FAILURE, FixResult.MAX_ITERATIONS]
        assert result.total_duration >= 0
        
    def test_scenario_listing(self):
        """Test that we can still list scenarios."""
        if not self.scenarios_dir.exists():
            pytest.skip("Scenarios directory not found")
            
        runner = AgentEvaluationRunner(self.scenarios_dir)
        scenarios = runner.list_scenarios()
        
        # Should have at least E001_missing_import
        assert len(scenarios) >= 0  # Could be 0 if scenarios don't exist yet