"""Configuration management for the agent."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import os
import json

from .config_schema import validate_agent_config, load_and_validate_config, config_validator


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
        """Load configuration from JSON file with validation."""
        try:
            validated_config = load_and_validate_config(config_path)
            return cls(**validated_config)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AgentConfig":
        """Create configuration from dictionary with validation."""
        try:
            validated_config = validate_agent_config(config_dict)
            return cls(**validated_config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "max_iterations": self.max_iterations,
            "max_session_duration": self.max_session_duration,
            "state_timeout": self.state_timeout,
            "max_cost_per_session": self.max_cost_per_session,
            "cost_warning_threshold": self.cost_warning_threshold,
            "max_diff_lines_per_file": self.max_diff_lines_per_file,
            "max_total_diff_lines": self.max_total_diff_lines,
            "require_approval_threshold": self.require_approval_threshold,
            "test_timeout": self.test_timeout,
            "search_max_results": self.search_max_results,
            "patch_backup": self.patch_backup,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "openai_api_key": self.openai_api_key,
            "openai_base_url": self.openai_base_url,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "blocked_paths": self.blocked_paths,
            "allowed_file_types": self.allowed_file_types
        }
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_iterations < 1 or self.max_iterations > 10:
            raise ValueError("max_iterations must be between 1 and 10")
        
        if self.max_cost_per_session < 0:
            raise ValueError("max_cost_per_session must be positive")
        
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        
        return True