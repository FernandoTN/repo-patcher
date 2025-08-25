"""Core state machine for the test fixing agent."""
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .models import (
    AgentSession, 
    AgentState, 
    StepResult, 
    StepExecution,
    RepositoryContext
)

logger = logging.getLogger(__name__)


class StateHandler(ABC):
    """Abstract base class for state handlers."""
    
    @abstractmethod
    async def execute(self, session: AgentSession) -> StepResult:
        """Execute the state logic."""
        pass
    
    @abstractmethod
    def get_state(self) -> AgentState:
        """Return the state this handler manages."""
        pass


class IngestHandler(StateHandler):
    """Handler for the INGEST state - analyze repository and failing tests."""
    
    def get_state(self) -> AgentState:
        return AgentState.INGEST
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Ingest repository information and identify failing tests."""
        logger.info(f"Ingesting repository: {session.repository.repo_path}")
        
        # TODO: Implement actual ingestion logic
        # - Clone/analyze repository structure
        # - Run tests to identify failures
        # - Parse test output
        # - Identify affected files
        
        # Mock implementation for now
        input_data = {"repo_path": str(session.repository.repo_path)}
        output_data = {
            "failing_tests": session.repository.failing_tests,
            "test_output": session.repository.test_output
        }
        
        return StepResult.SUCCESS


class PlanHandler(StateHandler):
    """Handler for the PLAN state - create fix strategy."""
    
    def get_state(self) -> AgentState:
        return AgentState.PLAN
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Create a plan for fixing the failing tests."""
        logger.info(f"Planning fixes for {len(session.repository.failing_tests)} failing tests")
        
        # TODO: Implement actual planning logic
        # - Analyze error messages
        # - Search codebase for relevant files
        # - Generate fix strategy
        # - Create step-by-step plan
        
        # Mock implementation for now
        input_data = {
            "failing_tests": session.repository.failing_tests,
            "iteration": session.iteration_count
        }
        output_data = {"plan_created": True}
        
        return StepResult.SUCCESS


class PatchHandler(StateHandler):
    """Handler for the PATCH state - apply code changes."""
    
    def get_state(self) -> AgentState:
        return AgentState.PATCH
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Apply the planned patches to fix the tests."""
        logger.info(f"Applying patches based on plan")
        
        # TODO: Implement actual patching logic
        # - Generate code changes
        # - Apply patches safely
        # - Create git commits
        # - Validate changes
        
        # Mock implementation for now
        input_data = {"plan": session.plan}
        output_data = {"patches_applied": len(session.patches)}
        
        return StepResult.SUCCESS


class TestHandler(StateHandler):
    """Handler for the TEST state - run tests and validate fixes."""
    
    def get_state(self) -> AgentState:
        return AgentState.TEST
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Run tests to validate the fixes."""
        logger.info("Running tests to validate fixes")
        
        # TODO: Implement actual test execution
        # - Run test suite
        # - Parse results
        # - Determine if fixes worked
        # - Collect new failures if any
        
        # Mock implementation for now - simulate success
        input_data = {"test_command": session.repository.test_command}
        output_data = {"tests_passed": True, "all_tests_pass": True}
        
        # For now, let's simulate success to test the flow
        return StepResult.SUCCESS


class RepairHandler(StateHandler):
    """Handler for the REPAIR state - fix issues from failed tests."""
    
    def get_state(self) -> AgentState:
        return AgentState.REPAIR
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Analyze test failures and prepare for another iteration."""
        logger.info(f"Repairing - iteration {session.iteration_count + 1}")
        
        # TODO: Implement actual repair logic
        # - Analyze what went wrong
        # - Update context with new failures
        # - Decide whether to retry or escalate
        
        # Mock implementation for now
        input_data = {"iteration": session.iteration_count}
        
        if session.iteration_count >= session.max_iterations:
            output_data = {"decision": "escalate"}
            return StepResult.ESCALATE
        else:
            output_data = {"decision": "retry"}
            return StepResult.RETRY


class PRHandler(StateHandler):
    """Handler for the PR state - create pull request."""
    
    def get_state(self) -> AgentState:
        return AgentState.PR
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Create a pull request with the fixes."""
        logger.info("Creating pull request with fixes")
        
        # TODO: Implement actual PR creation
        # - Generate PR title and description
        # - Create branch
        # - Push changes
        # - Open PR via GitHub API
        
        # Mock implementation for now
        input_data = {"patches": len(session.patches)}
        output_data = {"pr_url": "https://github.com/example/repo/pull/123"}
        
        return StepResult.SUCCESS


class AgentStateMachine:
    """Main state machine orchestrating the agent workflow."""
    
    def __init__(self):
        self.handlers: Dict[AgentState, StateHandler] = {
            AgentState.INGEST: IngestHandler(),
            AgentState.PLAN: PlanHandler(),
            AgentState.PATCH: PatchHandler(),
            AgentState.TEST: TestHandler(),
            AgentState.REPAIR: RepairHandler(),
            AgentState.PR: PRHandler(),
        }
    
    async def execute_session(self, repository: RepositoryContext) -> AgentSession:
        """Execute a complete agent session."""
        session = AgentSession(
            session_id=str(uuid.uuid4()),
            repository=repository,
            current_state=AgentState.INGEST
        )
        
        logger.info(f"Starting agent session {session.session_id}")
        
        while not session.is_complete:
            result = await self._execute_step(session)
            
            # Safety check to prevent infinite loops
            if len(session.executions) > 20:
                logger.error("Too many execution steps, escalating")
                session.current_state = AgentState.ESCALATED
                break
        
        session.end_time = time.time()
        logger.info(f"Session {session.session_id} completed in state {session.current_state.value}")
        
        return session
    
    async def _execute_step(self, session: AgentSession) -> StepResult:
        """Execute a single step in the state machine."""
        current_state = session.current_state
        
        if current_state not in self.handlers:
            logger.error(f"No handler for state {current_state}")
            session.current_state = AgentState.FAILED
            return StepResult.FAILURE
        
        handler = self.handlers[current_state]
        start_time = time.time()
        
        try:
            result = await handler.execute(session)
            duration = time.time() - start_time
            
            execution = StepExecution(
                state=current_state,
                result=result,
                duration=duration,
                input_data={"state": current_state.value},
                output_data={"result": result.value}
            )
            
            session.add_execution(execution)
            
            logger.info(f"State {current_state.value} completed with result {result.value}")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in state {current_state.value}: {e}")
            
            execution = StepExecution(
                state=current_state,
                result=StepResult.FAILURE,
                duration=duration,
                input_data={"state": current_state.value},
                output_data={},
                error_message=str(e)
            )
            
            session.add_execution(execution)
            session.current_state = AgentState.FAILED
            
            return StepResult.FAILURE