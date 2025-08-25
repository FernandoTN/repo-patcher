"""Custom exceptions for the agent."""


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class StateTransitionError(AgentError):
    """Error in state machine transitions."""
    pass


class InvalidStateError(AgentError):
    """Invalid state for current operation."""
    pass


class CostLimitExceededError(AgentError):
    """Cost limit exceeded during execution."""
    pass


class TimeoutError(AgentError):
    """Operation timed out."""
    pass


class SafetyViolationError(AgentError):
    """Safety constraint violated."""
    pass


class ToolExecutionError(AgentError):
    """Error executing a tool."""
    pass


class RepositoryError(AgentError):
    """Error with repository operations."""
    pass


class TestExecutionError(AgentError):
    """Error executing tests."""
    pass


class PatchApplicationError(AgentError):
    """Error applying code patches."""
    pass