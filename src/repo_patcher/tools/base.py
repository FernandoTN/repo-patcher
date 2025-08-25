"""Base classes and interfaces for agent tools."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

from ..agent.models import ToolCall


@dataclass
class ToolResult:
    """Result of executing a tool."""
    success: bool
    data: Any
    error: Optional[str] = None
    cost: float = 0.0
    duration: float = 0.0


class BaseTool(ABC):
    """Abstract base class for all agent tools."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with error handling and timing."""
        start_time = time.time()
        
        try:
            result = await self._execute(**kwargs)
            duration = time.time() - start_time
            
            return ToolResult(
                success=True,
                data=result,
                duration=duration,
                cost=self._calculate_cost(**kwargs)
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                duration=duration
            )
    
    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        """Implement the actual tool logic."""
        pass
    
    def _calculate_cost(self, **kwargs) -> float:
        """Calculate the cost of executing this tool."""
        return 0.0  # Override in subclasses that have costs
    
    def create_call_record(self, parameters: Dict[str, Any], result: ToolResult) -> ToolCall:
        """Create a record of this tool call."""
        return ToolCall(
            tool_name=self.name,
            parameters=parameters,
            result=result.data if result.success else None,
            duration=result.duration,
            cost=result.cost,
            error=result.error
        )