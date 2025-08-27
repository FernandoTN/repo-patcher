"""Enhanced structured logging with correlation IDs and metrics."""
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from contextlib import contextmanager, asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict
import threading

# Context variables for request tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
operation_var: ContextVar[Optional[str]] = ContextVar('operation', default=None)


@dataclass
class LogContext:
    """Structured logging context."""
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    start_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ContextualFormatter(logging.Formatter):
    """Formatter that includes context variables and structured data."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with context."""
        # Get context variables
        correlation_id = correlation_id_var.get()
        session_id = session_id_var.get() 
        operation = operation_var.get()
        
        # Build structured log entry
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context information
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        if session_id:
            log_entry["session_id"] = session_id
            
        if operation:
            log_entry["operation"] = operation
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'pathname', 'lineno', 'funcName',
                          'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'module', 'filename', 'levelno',
                          'levelname', 'message', 'exc_info', 'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add exception information
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """Structured logger with context management."""
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self._setup_handler()
    
    def _setup_handler(self):
        """Set up structured logging handler."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(ContextualFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self.logger.critical(message, extra=kwargs)


@contextmanager
def log_context(correlation_id: Optional[str] = None,
                session_id: Optional[str] = None, 
                operation: Optional[str] = None):
    """Context manager for setting logging context."""
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    
    # Set context variables
    token_corr = correlation_id_var.set(correlation_id)
    token_sess = session_id_var.set(session_id)
    token_op = operation_var.set(operation)
    
    try:
        yield correlation_id
    finally:
        # Reset context variables
        correlation_id_var.reset(token_corr)
        session_id_var.reset(token_sess)
        operation_var.reset(token_op)


@asynccontextmanager
async def operation_timer(logger: StructuredLogger, operation_name: str, **metadata):
    """Context manager for timing operations."""
    start_time = time.time()
    correlation_id = correlation_id_var.get() or str(uuid.uuid4())[:8]
    
    with log_context(correlation_id=correlation_id, operation=operation_name):
        logger.info(f"Starting operation: {operation_name}", 
                   operation=operation_name, **metadata)
        
        try:
            yield correlation_id
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Operation failed: {operation_name}",
                        operation=operation_name,
                        duration=duration,
                        error=str(e),
                        **metadata)
            raise
            
        else:
            duration = time.time() - start_time
            logger.info(f"Operation completed: {operation_name}",
                       operation=operation_name,
                       duration=duration,
                       **metadata)


class MetricsCollector:
    """Simple metrics collection for monitoring."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._metrics = {}
        self._lock = threading.Lock()
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._build_key(metric_name, tags)
            if key not in self._metrics:
                self._metrics[key] = {"type": "counter", "value": 0, "tags": tags or {}}
            self._metrics[key]["value"] += value
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self._lock:
            key = self._build_key(metric_name, tags)
            self._metrics[key] = {"type": "gauge", "value": value, "tags": tags or {}}
    
    def histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        with self._lock:
            key = self._build_key(metric_name, tags)
            if key not in self._metrics:
                self._metrics[key] = {"type": "histogram", "values": [], "tags": tags or {}}
            self._metrics[key]["values"].append(value)
    
    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimerContext(self, metric_name, tags)
    
    def _build_key(self, metric_name: str, tags: Optional[Dict[str, str]]) -> str:
        """Build metric key with tags."""
        if not tags:
            return metric_name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            return dict(self._metrics)
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]]):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.histogram(self.metric_name, duration, self.tags)


# Global instances
metrics = MetricsCollector()


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# Convenience functions for common operations
def log_api_call(logger: StructuredLogger, service: str, method: str, **kwargs):
    """Log an API call with standard fields."""
    logger.info(f"API call: {service}.{method}",
                service=service,
                method=method,
                **kwargs)


def log_performance(logger: StructuredLogger, operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    logger.info(f"Performance: {operation}",
                operation=operation,
                duration=duration,
                **kwargs)
    
    # Also record in metrics
    metrics.histogram(f"operation_duration", duration, {"operation": operation})


def log_cost(logger: StructuredLogger, operation: str, cost: float, currency: str = "USD", **kwargs):
    """Log cost metrics."""
    logger.info(f"Cost: {operation}",
                operation=operation,
                cost=cost,
                currency=currency,
                **kwargs)
    
    # Also record in metrics
    metrics.histogram(f"operation_cost", cost, {"operation": operation, "currency": currency})


def log_security_event(logger: StructuredLogger, event_type: str, severity: str = "medium", **kwargs):
    """Log security-related events."""
    logger.warning(f"Security event: {event_type}",
                   event_type=event_type,
                   severity=severity,
                   **kwargs)
    
    # Also record in metrics
    metrics.increment("security_events", 1, {"type": event_type, "severity": severity})