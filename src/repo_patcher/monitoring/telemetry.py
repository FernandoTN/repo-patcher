"""
OpenTelemetry integration for Repo Patcher monitoring and observability.

This module provides comprehensive monitoring including:
- Distributed tracing across all agent operations
- Custom metrics for success rates, costs, and performance
- Structured logging with trace correlation
- Health monitoring and alerting
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps

from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)


class TelemetryManager:
    """
    Manages OpenTelemetry setup and provides convenience methods for
    tracing, metrics, and monitoring throughout the Repo Patcher agent.
    """

    def __init__(self, service_name: str = "repo-patcher", service_version: str = "0.1.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.resource = None
        self.tracer = None
        self.meter = None
        self._initialized = False
        
        # Metrics storage
        self._counters: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing and metrics."""
        if self._initialized:
            return

        try:
            # Create resource with service information
            self.resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.SERVICE_INSTANCE_ID: os.environ.get("HOSTNAME", "unknown"),
            })

            # Initialize tracing
            self._setup_tracing()
            
            # Initialize metrics
            self._setup_metrics()
            
            # Initialize logging instrumentation
            LoggingInstrumentor().instrument()
            
            self._initialized = True
            logger.info("OpenTelemetry initialized successfully", extra={
                "service_name": self.service_name,
                "service_version": self.service_version
            })

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            raise

    def _setup_tracing(self) -> None:
        """Set up distributed tracing with Jaeger export."""
        # Configure tracer provider
        trace.set_tracer_provider(TracerProvider(resource=self.resource))
        
        # Get tracer
        self.tracer = trace.get_tracer(self.service_name, self.service_version)
        
        # Configure Jaeger exporter if endpoint is available
        jaeger_endpoint = os.environ.get("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                endpoint=jaeger_endpoint,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            logger.info(f"Jaeger tracing configured with endpoint: {jaeger_endpoint}")

    def _setup_metrics(self) -> None:
        """Set up metrics collection with Prometheus export."""
        # Configure Prometheus metrics reader
        prometheus_port = int(os.environ.get("PROMETHEUS_PORT", "8000"))
        reader = PrometheusMetricReader(port=prometheus_port)
        
        # Configure metrics provider
        metrics.set_meter_provider(MeterProvider(
            resource=self.resource,
            metric_readers=[reader]
        ))
        
        # Get meter
        self.meter = metrics.get_meter(self.service_name, self.service_version)
        
        # Create standard metrics
        self._create_standard_metrics()
        
        logger.info(f"Prometheus metrics configured on port: {prometheus_port}")

    def _create_standard_metrics(self) -> None:
        """Create standard metrics for Repo Patcher operations."""
        if not self.meter:
            return

        # Counters
        self._counters["fix_attempts"] = self.meter.create_counter(
            name="repo_patcher_fix_attempts_total",
            description="Total number of test fix attempts",
            unit="1"
        )
        
        self._counters["fix_successes"] = self.meter.create_counter(
            name="repo_patcher_fix_successes_total",
            description="Total number of successful test fixes",
            unit="1"
        )
        
        self._counters["errors"] = self.meter.create_counter(
            name="repo_patcher_errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        self._counters["rate_limited"] = self.meter.create_counter(
            name="repo_patcher_rate_limited_total",
            description="Total number of API rate limit events",
            unit="1"
        )

        # Histograms
        self._histograms["duration"] = self.meter.create_histogram(
            name="repo_patcher_duration_seconds",
            description="Duration of fix attempts in seconds",
            unit="s"
        )
        
        self._histograms["cost"] = self.meter.create_histogram(
            name="repo_patcher_cost_dollars",
            description="Cost of AI API calls in dollars",
            unit="$"
        )
        
        self._histograms["diff_lines"] = self.meter.create_histogram(
            name="repo_patcher_diff_lines",
            description="Number of lines changed in fixes",
            unit="lines"
        )

        # Gauges  
        self._gauges["active_sessions"] = self.meter.create_up_down_counter(
            name="repo_patcher_active_sessions",
            description="Number of active agent sessions",
            unit="1"
        )

    @contextmanager
    def trace_span(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for creating traced spans.
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Additional attributes to add to the span
        """
        if not self.tracer:
            # Fallback if not initialized
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    def trace_function(self, operation_name: Optional[str] = None):
        """
        Decorator for automatically tracing function calls.
        
        Args:
            operation_name: Custom operation name (defaults to function name)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"
                with self.trace_span(name, {"function": func.__name__}):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def record_fix_attempt(self, success: bool, duration: float, cost: float = 0.0,
                          lines_changed: int = 0, attributes: Optional[Dict[str, Any]] = None):
        """
        Record metrics for a fix attempt.
        
        Args:
            success: Whether the fix was successful
            duration: Duration of the fix attempt in seconds
            cost: Cost of API calls in dollars
            lines_changed: Number of lines changed
            attributes: Additional attributes for the metrics
        """
        if not self._initialized:
            return

        labels = attributes or {}
        
        # Record attempt counter
        self._counters["fix_attempts"].add(1, labels)
        
        # Record success counter if successful
        if success:
            self._counters["fix_successes"].add(1, labels)
        
        # Record duration histogram
        self._histograms["duration"].record(duration, labels)
        
        # Record cost if provided
        if cost > 0:
            self._histograms["cost"].record(cost, labels)
        
        # Record lines changed if provided
        if lines_changed > 0:
            self._histograms["diff_lines"].record(lines_changed, labels)

    def record_error(self, error_type: str, error_message: str = "",
                    attributes: Optional[Dict[str, Any]] = None):
        """
        Record an error metric.
        
        Args:
            error_type: Type/category of the error
            error_message: Error message
            attributes: Additional attributes
        """
        if not self._initialized:
            return

        labels = attributes or {}
        labels["error_type"] = error_type
        
        if error_message:
            labels["error_message"] = error_message[:100]  # Truncate long messages
        
        self._counters["errors"].add(1, labels)

    def record_rate_limit(self, api_name: str = "openai", attributes: Optional[Dict[str, Any]] = None):
        """
        Record a rate limit event.
        
        Args:
            api_name: Name of the API that was rate limited
            attributes: Additional attributes
        """
        if not self._initialized:
            return

        labels = attributes or {}
        labels["api"] = api_name
        
        self._counters["rate_limited"].add(1, labels)

    def update_active_sessions(self, delta: int, attributes: Optional[Dict[str, Any]] = None):
        """
        Update the active sessions gauge.
        
        Args:
            delta: Change in active sessions (+1 for new, -1 for ended)
            attributes: Additional attributes
        """
        if not self._initialized:
            return

        labels = attributes or {}
        self._gauges["active_sessions"].add(delta, labels)

    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID for correlation."""
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_id = current_span.get_span_context().trace_id
            return f"{trace_id:032x}"
        return None

    def get_current_span_id(self) -> Optional[str]:
        """Get the current span ID for correlation."""
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            span_id = current_span.get_span_context().span_id
            return f"{span_id:016x}"
        return None

    def shutdown(self):
        """Shutdown telemetry and flush pending data."""
        try:
            # Flush any pending traces
            if hasattr(trace.get_tracer_provider(), 'shutdown'):
                trace.get_tracer_provider().shutdown()
            
            # Flush any pending metrics
            if hasattr(metrics.get_meter_provider(), 'shutdown'):
                metrics.get_meter_provider().shutdown()
                
            logger.info("OpenTelemetry shutdown completed")
        except Exception as e:
            logger.error(f"Error during OpenTelemetry shutdown: {e}")


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """Get the global telemetry manager instance."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
        # Auto-initialize if environment indicates it should be enabled
        if os.environ.get("OTEL_ENABLED", "false").lower() == "true":
            _telemetry_manager.initialize()
    return _telemetry_manager


def initialize_telemetry(service_name: str = "repo-patcher", service_version: str = "0.1.0") -> TelemetryManager:
    """
    Initialize the global telemetry manager.
    
    Args:
        service_name: Service name for telemetry
        service_version: Service version
    
    Returns:
        Initialized telemetry manager
    """
    global _telemetry_manager
    _telemetry_manager = TelemetryManager(service_name, service_version)
    _telemetry_manager.initialize()
    return _telemetry_manager


# Convenience functions using global manager
def trace_span(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Convenience function for creating traced spans."""
    return get_telemetry_manager().trace_span(operation_name, attributes)


def trace_function(operation_name: Optional[str] = None):
    """Convenience decorator for tracing functions."""
    return get_telemetry_manager().trace_function(operation_name)


def record_fix_attempt(success: bool, duration: float, cost: float = 0.0,
                      lines_changed: int = 0, attributes: Optional[Dict[str, Any]] = None):
    """Convenience function for recording fix attempts."""
    get_telemetry_manager().record_fix_attempt(success, duration, cost, lines_changed, attributes)


def record_error(error_type: str, error_message: str = "", attributes: Optional[Dict[str, Any]] = None):
    """Convenience function for recording errors."""
    get_telemetry_manager().record_error(error_type, error_message, attributes)


def record_rate_limit(api_name: str = "openai", attributes: Optional[Dict[str, Any]] = None):
    """Convenience function for recording rate limits."""
    get_telemetry_manager().record_rate_limit(api_name, attributes)