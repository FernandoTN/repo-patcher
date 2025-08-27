"""Input validation and sanitization for the agent."""
import re
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Input validation error."""
    pass


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    # Security patterns to detect potential attacks
    INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",  # Shell injection characters
        r"\.\.\/",             # Directory traversal
        r"<script",           # XSS attempts
        r"javascript:",       # JavaScript injection
        r"eval\s*\(",         # Code evaluation
        r"exec\s*\(",         # Code execution
        r"import\s+",         # Python import injection
        r"__.*__",            # Python dunder methods
    ]
    
    # Safe filename pattern
    SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
    
    # Safe path pattern (no traversal, no special chars)
    SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
    
    def __init__(self, max_string_length: int = 10000, max_list_size: int = 1000):
        """Initialize validator with limits."""
        self.max_string_length = max_string_length
        self.max_list_size = max_list_size
    
    def validate_string(self, value: str, field_name: str = "input", allow_empty: bool = False) -> str:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")
        
        if not allow_empty and not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")
        
        if len(value) > self.max_string_length:
            raise ValidationError(f"{field_name} exceeds maximum length of {self.max_string_length}")
        
        # Check for injection patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potential injection attempt detected in {field_name}: {pattern}")
                raise ValidationError(f"{field_name} contains potentially unsafe characters")
        
        return value.strip()
    
    def validate_path(self, path: Union[str, Path], field_name: str = "path") -> Path:
        """Validate file path for safety."""
        if isinstance(path, str):
            path = Path(path)
        
        path_str = str(path)
        
        # Check for directory traversal
        if ".." in path_str:
            raise ValidationError(f"{field_name} contains directory traversal attempts")
        
        # Check for absolute paths outside allowed areas
        if path.is_absolute():
            # Allow specific safe absolute paths
            safe_prefixes = ["/tmp", "/var/tmp", str(Path.home()), str(Path.cwd())]
            if not any(path_str.startswith(prefix) for prefix in safe_prefixes):
                raise ValidationError(f"{field_name} points to restricted absolute path")
        
        # Resolve and check final path
        try:
            resolved_path = path.resolve()
            # Ensure resolved path doesn't escape to system directories
            system_dirs = ["/etc", "/usr", "/bin", "/sbin", "/sys", "/proc"]
            if any(str(resolved_path).startswith(sys_dir) for sys_dir in system_dirs):
                raise ValidationError(f"{field_name} resolves to restricted system directory")
        except Exception as e:
            raise ValidationError(f"{field_name} cannot be resolved: {e}")
        
        return path
    
    def validate_filename(self, filename: str, field_name: str = "filename") -> str:
        """Validate filename for safety."""
        filename = self.validate_string(filename, field_name)
        
        if not self.SAFE_FILENAME_PATTERN.match(filename):
            raise ValidationError(f"{field_name} contains unsafe characters")
        
        # Check for reserved names
        reserved_names = ["CON", "PRN", "AUX", "NUL"] + [f"COM{i}" for i in range(1, 10)]
        if filename.upper() in reserved_names:
            raise ValidationError(f"{field_name} is a reserved system name")
        
        return filename
    
    def validate_list(self, value: List[Any], field_name: str = "list", 
                     item_validator=None) -> List[Any]:
        """Validate list input."""
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list, got {type(value).__name__}")
        
        if len(value) > self.max_list_size:
            raise ValidationError(f"{field_name} exceeds maximum size of {self.max_list_size}")
        
        if item_validator:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = item_validator(item, f"{field_name}[{i}]")
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f"{field_name}[{i}]: {e}")
            return validated_items
        
        return value
    
    def validate_dict(self, value: Dict[str, Any], field_name: str = "dict",
                     required_keys: Optional[List[str]] = None,
                     optional_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate dictionary input."""
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be a dictionary, got {type(value).__name__}")
        
        # Check required keys
        if required_keys:
            missing_keys = set(required_keys) - set(value.keys())
            if missing_keys:
                raise ValidationError(f"{field_name} missing required keys: {missing_keys}")
        
        # Check for unexpected keys
        if required_keys is not None or optional_keys is not None:
            allowed_keys = set(required_keys or []) | set(optional_keys or [])
            unexpected_keys = set(value.keys()) - allowed_keys
            if unexpected_keys:
                raise ValidationError(f"{field_name} contains unexpected keys: {unexpected_keys}")
        
        return value
    
    def validate_openai_key(self, api_key: str) -> str:
        """Validate OpenAI API key format."""
        api_key = self.validate_string(api_key, "OpenAI API key")
        
        if not api_key.startswith("sk-"):
            raise ValidationError("OpenAI API key must start with 'sk-'")
        
        if len(api_key) < 20:  # Minimum reasonable length
            raise ValidationError("OpenAI API key appears to be too short")
        
        return api_key
    
    def validate_model_name(self, model_name: str) -> str:
        """Validate AI model name."""
        model_name = self.validate_string(model_name, "model name")
        
        # Whitelist of known safe models
        allowed_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
            "text-davinci-003", "text-davinci-002"
        ]
        
        if model_name not in allowed_models:
            logger.warning(f"Using non-whitelisted model: {model_name}")
            # Don't reject, but log for monitoring
        
        return model_name
    
    def validate_temperature(self, temperature: float) -> float:
        """Validate temperature parameter."""
        if not isinstance(temperature, (int, float)):
            raise ValidationError(f"Temperature must be a number, got {type(temperature).__name__}")
        
        if not 0.0 <= temperature <= 2.0:
            raise ValidationError("Temperature must be between 0.0 and 2.0")
        
        return float(temperature)
    
    def validate_max_tokens(self, max_tokens: int) -> int:
        """Validate max tokens parameter."""
        if not isinstance(max_tokens, int):
            raise ValidationError(f"Max tokens must be an integer, got {type(max_tokens).__name__}")
        
        if max_tokens <= 0:
            raise ValidationError("Max tokens must be positive")
        
        if max_tokens > 128000:  # Current GPT-4 limit
            raise ValidationError("Max tokens exceeds reasonable limit (128,000)")
        
        return max_tokens
    
    def sanitize_log_message(self, message: str) -> str:
        """Sanitize log message to prevent log injection."""
        if not isinstance(message, str):
            return str(message)
        
        # Remove newlines and tabs that could break log format
        sanitized = message.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        
        # Truncate very long messages
        if len(sanitized) > 1000:
            sanitized = sanitized[:997] + "..."
        
        return sanitized
    
    def validate_repository_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate repository context input."""
        required_keys = ["repo_path", "repo_url", "branch", "test_framework", "test_command"]
        optional_keys = ["commit_sha", "failing_tests", "test_output"]
        
        context = self.validate_dict(context, "repository context", required_keys, optional_keys)
        
        # Validate specific fields
        context["repo_path"] = str(self.validate_path(context["repo_path"], "repo_path"))
        context["repo_url"] = self.validate_string(context["repo_url"], "repo_url")
        context["branch"] = self.validate_string(context["branch"], "branch")
        context["test_framework"] = self.validate_string(context["test_framework"], "test_framework")
        context["test_command"] = self.validate_string(context["test_command"], "test_command")
        
        if "failing_tests" in context:
            context["failing_tests"] = self.validate_list(
                context["failing_tests"], "failing_tests",
                lambda x, name: self.validate_string(x, name)
            )
        
        return context


# Global validator instance
default_validator = InputValidator()


def validate_input(data: Any, validator_func_name: str, **kwargs) -> Any:
    """Convenience function for input validation."""
    if not hasattr(default_validator, validator_func_name):
        raise ValueError(f"Unknown validator function: {validator_func_name}")
    
    validator_func = getattr(default_validator, validator_func_name)
    return validator_func(data, **kwargs)