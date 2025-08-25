"""Data models for the agent state machine."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path
import time

from .config import AgentConfig
from .context import SessionContext


class AgentState(Enum):
    """States in the agent execution workflow."""
    IDLE = "idle"
    INGEST = "ingest"
    PLAN = "plan" 
    PATCH = "patch"
    TEST = "test"
    REPAIR = "repair"
    PR = "pr"
    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"


class StepResult(Enum):
    """Result of executing a state machine step."""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass
class RepositoryContext:
    """Context about the repository being fixed."""
    repo_path: Path
    repo_url: str
    branch: str
    commit_sha: str
    test_framework: str
    test_command: str
    failing_tests: List[str] = field(default_factory=list)
    test_output: str = ""
    

@dataclass 
class PlanStep:
    """Individual step in the fix plan."""
    description: str
    file_path: str
    change_type: str  # "modify", "add", "delete"
    reasoning: str
    confidence: float


@dataclass
class FixPlan:
    """Plan for fixing the failing tests."""
    summary: str
    steps: List[PlanStep]
    estimated_iterations: int
    risk_level: str  # "low", "medium", "high"
    total_confidence: float


@dataclass
class CodePatch:
    """A code patch to apply."""
    file_path: str
    old_content: str
    new_content: str
    diff: str
    reasoning: str
    lines_added: int
    lines_removed: int
    lines_modified: int


@dataclass
class StepExecution:
    """Record of executing a state machine step."""
    state: AgentState
    result: StepResult
    duration: float
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error_message: Optional[str] = None
    cost: float = 0.0


@dataclass
class AgentSession:
    """Complete agent execution session."""
    session_id: str
    repository: RepositoryContext
    current_state: AgentState
    config: AgentConfig = field(default_factory=AgentConfig)
    context: SessionContext = field(default_factory=SessionContext)
    plan: Optional[FixPlan] = None
    patches: List[CodePatch] = field(default_factory=list)
    executions: List[StepExecution] = field(default_factory=list)
    iteration_count: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_cost: float = 0.0
    
    @property 
    def max_iterations(self) -> int:
        """Get max iterations from config."""
        return self.config.max_iterations
    
    @property
    def is_complete(self) -> bool:
        """Check if session is in a terminal state."""
        return self.current_state in [
            AgentState.DONE, 
            AgentState.FAILED, 
            AgentState.ESCALATED
        ]
    
    @property
    def duration(self) -> float:
        """Total session duration."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def add_execution(self, execution: StepExecution) -> None:
        """Add execution record and update totals."""
        self.executions.append(execution)
        self.total_cost += execution.cost
        
        # Update state based on execution result
        if execution.result == StepResult.SUCCESS:
            self._advance_state()
        elif execution.result == StepResult.FAILURE:
            self.current_state = AgentState.FAILED
        elif execution.result == StepResult.ESCALATE:
            self.current_state = AgentState.ESCALATED
        elif execution.result == StepResult.RETRY:
            if self.current_state == AgentState.REPAIR:
                self.iteration_count += 1
                if self.iteration_count >= self.max_iterations:
                    self.current_state = AgentState.ESCALATED
                else:
                    self.current_state = AgentState.PLAN  # Go back to planning
    
    def _advance_state(self) -> None:
        """Advance to the next state in the workflow."""
        state_transitions = {
            AgentState.IDLE: AgentState.INGEST,
            AgentState.INGEST: AgentState.PLAN,
            AgentState.PLAN: AgentState.PATCH,
            AgentState.PATCH: AgentState.TEST,
            AgentState.TEST: AgentState.DONE,  # If tests pass
            AgentState.REPAIR: AgentState.PLAN,  # Back to planning
        }
        
        if self.current_state in state_transitions:
            self.current_state = state_transitions[self.current_state]
    
    def set_test_failure(self) -> None:
        """Set state to repair when tests fail."""
        if self.current_state == AgentState.TEST:
            self.current_state = AgentState.REPAIR
    
    def check_cost_limit(self) -> bool:
        """Check if cost limit has been exceeded."""
        return self.total_cost >= self.config.max_cost_per_session
    
    def check_time_limit(self) -> bool:
        """Check if time limit has been exceeded."""
        return self.duration >= self.config.max_session_duration
    
    def is_safe_to_continue(self) -> bool:
        """Check if it's safe to continue execution."""
        return not (self.check_cost_limit() or self.check_time_limit())
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the session."""
        return {
            "session_id": self.session_id,
            "state": self.current_state.value,
            "iterations": self.iteration_count,
            "duration": self.duration,
            "cost": self.total_cost,
            "executions": len(self.executions),
            "patches": len(self.patches),
            "complete": self.is_complete
        }


@dataclass
class ToolCall:
    """Record of a tool being called."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    duration: float
    cost: float = 0.0
    error: Optional[str] = None