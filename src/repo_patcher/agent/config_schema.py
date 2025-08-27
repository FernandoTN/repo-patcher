"""JSON schema validation for configuration files."""
from typing import Dict, Any, Optional
import json
from pathlib import Path
from jsonschema import validate, ValidationError as JSONValidationError

# Configuration JSON Schema
AGENT_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Agent Configuration Schema",
    "description": "Configuration schema for the Repo Patcher agent",
    "type": "object",
    "properties": {
        "max_iterations": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 3,
            "description": "Maximum number of repair iterations"
        },
        "max_session_duration": {
            "type": "integer",
            "minimum": 60,
            "maximum": 3600,
            "default": 600,
            "description": "Maximum session duration in seconds"
        },
        "state_timeout": {
            "type": "integer",
            "minimum": 30,
            "maximum": 600,
            "default": 120,
            "description": "Timeout per state in seconds"
        },
        "max_cost_per_session": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 100.0,
            "default": 5.0,
            "description": "Maximum cost per session in USD"
        },
        "cost_warning_threshold": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 100.0,
            "default": 2.0,
            "description": "Cost warning threshold in USD"
        },
        "max_diff_lines_per_file": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 100,
            "description": "Maximum diff lines per file"
        },
        "max_total_diff_lines": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5000,
            "default": 500,
            "description": "Maximum total diff lines"
        },
        "require_approval_threshold": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "default": 50,
            "description": "Lines requiring human approval"
        },
        "test_timeout": {
            "type": "integer",
            "minimum": 10,
            "maximum": 600,
            "default": 60,
            "description": "Test execution timeout in seconds"
        },
        "search_max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 20,
            "description": "Maximum search results"
        },
        "patch_backup": {
            "type": "boolean",
            "default": True,
            "description": "Enable patch backup"
        },
        "model_name": {
            "type": "string",
            "pattern": "^(gpt-4|gpt-4-turbo|gpt-4o|gpt-4o-mini|gpt-3.5-turbo).*$",
            "default": "gpt-4o-mini",
            "description": "OpenAI model name"
        },
        "temperature": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 2.0,
            "default": 0.1,
            "description": "AI temperature setting"
        },
        "max_tokens": {
            "type": "integer",
            "minimum": 100,
            "maximum": 128000,
            "default": 4000,
            "description": "Maximum tokens per request"
        },
        "openai_api_key": {
            "type": ["string", "null"],
            "pattern": "^sk-[A-Za-z0-9_-]+$",
            "description": "OpenAI API key"
        },
        "openai_base_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "Custom OpenAI base URL"
        },
        "retry_attempts": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
            "default": 3,
            "description": "Number of retry attempts for API calls"
        },
        "retry_delay": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 30.0,
            "default": 1.0,
            "description": "Initial retry delay in seconds"
        },
        "blocked_paths": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1
            },
            "uniqueItems": True,
            "default": [
                ".github/", ".git/", "Dockerfile", "docker-compose.yml",
                "*.env", "*.key", "*.pem", "*secret*", "*config*"
            ],
            "description": "Blocked file paths and patterns"
        },
        "allowed_file_types": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^\\.[a-z0-9]+$"
            },
            "uniqueItems": True,
            "default": [
                ".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".h",
                ".rb", ".php", ".cs", ".rs", ".kt", ".swift", ".scala"
            ],
            "description": "Allowed file extensions"
        }
    },
    "additionalProperties": False
}

# Repository Context Schema
REPOSITORY_CONTEXT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Repository Context Schema",
    "description": "Schema for repository context data",
    "type": "object",
    "required": ["repo_path", "repo_url", "branch", "test_framework", "test_command"],
    "properties": {
        "repo_path": {
            "type": "string",
            "minLength": 1,
            "description": "Path to repository"
        },
        "repo_url": {
            "type": "string",
            "format": "uri",
            "description": "Repository URL"
        },
        "branch": {
            "type": "string",
            "minLength": 1,
            "pattern": "^[a-zA-Z0-9_/-]+$",
            "description": "Git branch name"
        },
        "commit_sha": {
            "type": "string",
            "pattern": "^[a-f0-9]{7,40}$",
            "description": "Git commit SHA"
        },
        "test_framework": {
            "type": "string",
            "enum": ["pytest", "jest", "go", "junit", "rspec", "phpunit", "mocha"],
            "description": "Test framework"
        },
        "test_command": {
            "type": "string",
            "minLength": 1,
            "description": "Command to run tests"
        },
        "failing_tests": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1
            },
            "uniqueItems": True,
            "description": "List of failing tests"
        },
        "test_output": {
            "type": "string",
            "description": "Test execution output"
        }
    },
    "additionalProperties": False
}

# Session Context Schema
SESSION_CONTEXT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Session Context Schema",
    "description": "Schema for agent session context",
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "pattern": "^[a-f0-9-]{36}$",
            "description": "Session UUID"
        },
        "code_context": {
            "type": "object",
            "properties": {
                "file_structure": {"type": "object"},
                "imports_map": {"type": "object"},
                "function_signatures": {"type": "object"},
                "class_hierarchy": {"type": "object"},
                "test_patterns": {"type": "array"},
                "dependencies": {"type": "array"}
            },
            "additionalProperties": True
        },
        "conversation": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["role", "content"],
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant", "system"]
                            },
                            "content": {"type": "string"}
                        }
                    }
                },
                "system_prompt": {"type": "string"},
                "previous_attempts": {"type": "array"},
                "learned_patterns": {"type": "object"}
            },
            "additionalProperties": False
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True
        }
    },
    "additionalProperties": True
}


class ConfigValidator:
    """Configuration validator with schema support."""
    
    def __init__(self):
        """Initialize validator."""
        self.schemas = {
            "agent_config": AGENT_CONFIG_SCHEMA,
            "repository_context": REPOSITORY_CONTEXT_SCHEMA,
            "session_context": SESSION_CONTEXT_SCHEMA
        }
    
    def validate_config(self, config_data: Dict[str, Any], schema_name: str = "agent_config") -> Dict[str, Any]:
        """
        Validate configuration against schema.
        
        Args:
            config_data: Configuration data to validate
            schema_name: Name of schema to use
            
        Returns:
            Validated configuration data
            
        Raises:
            ValidationError: If validation fails
        """
        if schema_name not in self.schemas:
            raise ValueError(f"Unknown schema: {schema_name}")
        
        schema = self.schemas[schema_name]
        
        try:
            validate(instance=config_data, schema=schema)
        except JSONValidationError as e:
            raise ConfigValidationError(f"Configuration validation failed: {e.message}") from e
        
        return config_data
    
    def validate_config_file(self, config_path: Path, schema_name: str = "agent_config") -> Dict[str, Any]:
        """
        Validate configuration file.
        
        Args:
            config_path: Path to configuration file
            schema_name: Name of schema to use
            
        Returns:
            Validated configuration data
            
        Raises:
            ValidationError: If validation fails
        """
        if not config_path.exists():
            raise ConfigValidationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in configuration file: {e}") from e
        except Exception as e:
            raise ConfigValidationError(f"Error reading configuration file: {e}") from e
        
        return self.validate_config(config_data, schema_name)
    
    def generate_default_config(self, schema_name: str = "agent_config") -> Dict[str, Any]:
        """
        Generate default configuration from schema.
        
        Args:
            schema_name: Name of schema to use
            
        Returns:
            Default configuration
        """
        if schema_name not in self.schemas:
            raise ValueError(f"Unknown schema: {schema_name}")
        
        schema = self.schemas[schema_name]
        default_config = {}
        
        def extract_defaults(schema_obj: Dict[str, Any], config_obj: Dict[str, Any]):
            """Recursively extract default values from schema."""
            if "properties" in schema_obj:
                for prop_name, prop_schema in schema_obj["properties"].items():
                    if "default" in prop_schema:
                        config_obj[prop_name] = prop_schema["default"]
                    elif prop_schema.get("type") == "object":
                        config_obj[prop_name] = {}
                        extract_defaults(prop_schema, config_obj[prop_name])
        
        extract_defaults(schema, default_config)
        return default_config
    
    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Get schema by name."""
        if schema_name not in self.schemas:
            raise ValueError(f"Unknown schema: {schema_name}")
        return self.schemas[schema_name].copy()


class ConfigValidationError(Exception):
    """Configuration validation error."""
    pass


# Global validator instance
config_validator = ConfigValidator()


def validate_agent_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate agent configuration."""
    return config_validator.validate_config(config_data, "agent_config")


def validate_repository_context(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate repository context."""
    return config_validator.validate_config(context_data, "repository_context")


def load_and_validate_config(config_path: Path) -> Dict[str, Any]:
    """Load and validate configuration file."""
    return config_validator.validate_config_file(config_path, "agent_config")