"""Configuration management for the agent."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import os


@dataclass
class AgentConfig:
    """Configuration for agent execution."""
    
    # State machine settings
    max_iterations: int = 3
    max_session_duration: int = 600  # 10 minutes in seconds
    state_timeout: int = 120  # 2 minutes per state
    
    # Cost limits
    max_cost_per_session: float = 5.0  # $5 per session
    cost_warning_threshold: float = 2.0  # Warn at $2
    
    # Safety settings
    max_diff_lines_per_file: int = 100
    max_total_diff_lines: int = 500
    require_approval_threshold: int = 50
    
    # Tool settings
    test_timeout: int = 60
    search_max_results: int = 20
    patch_backup: bool = True
    
    # AI settings
    model_name: str = "gpt-4o-mini"  # Using gpt-4o-mini as requested (gpt-5-nano not available)
    temperature: float = 0.1
    max_tokens: int = 4000
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # File restrictions
    blocked_paths: list = None
    allowed_file_types: list = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.blocked_paths is None:
            self.blocked_paths = [
                ".github/", ".git/", "Dockerfile", "docker-compose.yml",
                "*.env", "*.key", "*.pem", "*secret*", "*config*"
            ]
        
        if self.allowed_file_types is None:
            self.allowed_file_types = [
                ".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".h",
                ".rb", ".php", ".cs", ".rs", ".kt", ".swift", ".scala"
            ]
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "3")),
            max_cost_per_session=float(os.getenv("AGENT_MAX_COST", "5.0")),
            model_name=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.1")),
            test_timeout=int(os.getenv("AGENT_TEST_TIMEOUT", "60")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            retry_attempts=int(os.getenv("AGENT_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("AGENT_RETRY_DELAY", "1.0")),
        )
    
    @classmethod
    def from_file(cls, config_path: Path) -> "AgentConfig":
        """Load configuration from JSON/YAML file."""
        # TODO: Implement file loading
        return cls()
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_iterations < 1 or self.max_iterations > 10:
            raise ValueError("max_iterations must be between 1 and 10")
        
        if self.max_cost_per_session < 0:
            raise ValueError("max_cost_per_session must be positive")
        
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        
        return True