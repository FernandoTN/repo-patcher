"""Logging configuration for the agent."""
import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class AgentFormatter(logging.Formatter):
    """Custom formatter for agent logs."""
    
    def __init__(self):
        super().__init__()
        self.fmt = "{asctime} | {levelname:8} | {name:20} | {message}"
        self.style = "{"
        
    def format(self, record):
        # Add session_id if available
        if hasattr(record, 'session_id'):
            record.name = f"{record.name}[{record.session_id[:8]}]"
        
        # Color coding for different levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        
        reset = '\033[0m'
        color = colors.get(record.levelname, '')
        
        # Format the message
        formatted = super().format(record)
        
        # Add color if outputting to terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            return f"{color}{formatted}{reset}"
        
        return formatted


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add session context if available
        if hasattr(record, 'session_id'):
            log_data["session_id"] = record.session_id
        
        if hasattr(record, 'state'):
            log_data["state"] = record.state
            
        if hasattr(record, 'duration'):
            log_data["duration"] = record.duration
            
        if hasattr(record, 'cost'):
            log_data["cost"] = record.cost
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = False,
    session_id: Optional[str] = None
) -> None:
    """Set up logging configuration for the agent."""
    
    # Get the root logger for our package
    logger = logging.getLogger("repo_patcher")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(AgentFormatter())
    
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files
        
        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_formatter = logging.Formatter(
                "{asctime} | {levelname:8} | {name:20} | {funcName:15} | {message}",
                style="{"
            )
            file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    # Add session context if provided
    if session_id:
        class SessionFilter(logging.Filter):
            def filter(self, record):
                record.session_id = session_id
                return True
        
        logger.addFilter(SessionFilter())


def get_agent_logger(name: str) -> logging.Logger:
    """Get a logger for agent components."""
    return logging.getLogger(f"repo_patcher.{name}")


# Context manager for adding session context
class LoggingSession:
    """Context manager for session-specific logging."""
    
    def __init__(self, session_id: str, state: Optional[str] = None):
        self.session_id = session_id
        self.state = state
        self.filter = None
        
    def __enter__(self):
        class SessionFilter(logging.Filter):
            def __init__(self, session_id: str, state: Optional[str] = None):
                super().__init__()
                self.session_id = session_id
                self.state = state
                
            def filter(self, record):
                record.session_id = self.session_id
                if self.state:
                    record.state = self.state
                return True
        
        self.filter = SessionFilter(self.session_id, self.state)
        
        logger = logging.getLogger("repo_patcher")
        logger.addFilter(self.filter)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.filter:
            logger = logging.getLogger("repo_patcher")
            logger.removeFilter(self.filter)