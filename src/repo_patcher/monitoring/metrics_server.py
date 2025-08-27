"""
Metrics HTTP server for Prometheus scraping.

This module provides an HTTP server that exposes Prometheus metrics
and health endpoints for monitoring Repo Patcher operations.
"""

import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from .health import get_health_report, HealthStatus
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics and health endpoints."""

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.debug(f"MetricsServer: {format % args}")

    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == "/metrics":
                self._handle_metrics()
            elif path == "/health":
                self._handle_health()
            elif path == "/health/live":
                self._handle_liveness()
            elif path == "/health/ready":
                self._handle_readiness()
            elif path == "/":
                self._handle_root()
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self._send_error(500, "Internal Server Error")

    def _handle_metrics(self):
        """Handle /metrics endpoint for Prometheus scraping."""
        try:
            # This would normally be handled by the PrometheusMetricReader
            # but we'll provide a basic implementation
            metrics_data = self._generate_prometheus_metrics()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.send_header('Content-Length', str(len(metrics_data)))
            self.end_headers()
            self.wfile.write(metrics_data.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            self._send_error(500, "Error generating metrics")

    def _handle_health(self):
        """Handle /health endpoint."""
        health_report = get_health_report()
        
        # Determine HTTP status code based on health
        if health_report.status == HealthStatus.HEALTHY:
            status_code = 200
        elif health_report.status == HealthStatus.DEGRADED:
            status_code = 200  # Still operational
        else:
            status_code = 503  # Service unavailable
        
        response_data = {
            "status": health_report.status.value,
            "timestamp": health_report.timestamp,
            "uptime": health_report.uptime,
            "version": health_report.version,
            "summary": health_report.summary,
            "checks": health_report.checks
        }
        
        self._send_json_response(response_data, status_code)

    def _handle_liveness(self):
        """Handle /health/live endpoint (Kubernetes liveness probe)."""
        # Simple liveness check - just return 200 if server is running
        response_data = {
            "status": "alive",
            "timestamp": get_health_report().timestamp
        }
        self._send_json_response(response_data, 200)

    def _handle_readiness(self):
        """Handle /health/ready endpoint (Kubernetes readiness probe)."""
        health_report = get_health_report()
        
        # Ready if healthy or degraded (but not unhealthy/unknown)
        ready = health_report.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        
        response_data = {
            "status": "ready" if ready else "not_ready",
            "health_status": health_report.status.value,
            "timestamp": health_report.timestamp
        }
        
        status_code = 200 if ready else 503
        self._send_json_response(response_data, status_code)

    def _handle_root(self):
        """Handle root endpoint with basic info."""
        response_data = {
            "service": "repo-patcher",
            "version": "0.1.0",
            "endpoints": {
                "/metrics": "Prometheus metrics",
                "/health": "Comprehensive health check",
                "/health/live": "Liveness probe",
                "/health/ready": "Readiness probe"
            }
        }
        self._send_json_response(response_data, 200)

    def _generate_prometheus_metrics(self) -> str:
        """Generate Prometheus-formatted metrics."""
        # This is a basic implementation - in practice, the PrometheusMetricReader
        # would handle this automatically
        
        health_report = get_health_report()
        
        metrics = []
        
        # Service info
        metrics.append(f'# HELP repo_patcher_info Service information')
        metrics.append(f'# TYPE repo_patcher_info gauge')
        metrics.append(f'repo_patcher_info{{version="0.1.0"}} 1')
        
        # Uptime
        metrics.append(f'# HELP repo_patcher_uptime_seconds Service uptime in seconds')
        metrics.append(f'# TYPE repo_patcher_uptime_seconds counter')
        metrics.append(f'repo_patcher_uptime_seconds {health_report.uptime}')
        
        # Health status (0=unknown, 1=unhealthy, 2=degraded, 3=healthy)
        status_value = {
            HealthStatus.UNKNOWN: 0,
            HealthStatus.UNHEALTHY: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.HEALTHY: 3
        }.get(health_report.status, 0)
        
        metrics.append(f'# HELP repo_patcher_health_status Current health status')
        metrics.append(f'# TYPE repo_patcher_health_status gauge')
        metrics.append(f'repo_patcher_health_status {status_value}')
        
        # Individual check statuses
        metrics.append(f'# HELP repo_patcher_check_status Individual health check status')
        metrics.append(f'# TYPE repo_patcher_check_status gauge')
        
        for check_name, check_result in health_report.checks.items():
            check_status = check_result.get("status", "unknown")
            check_status_value = {
                "unknown": 0,
                "unhealthy": 1,
                "degraded": 2,
                "healthy": 3
            }.get(check_status, 0)
            
            is_critical = check_result.get("critical", False)
            metrics.append(f'repo_patcher_check_status{{check="{check_name}",critical="{is_critical}"}} {check_status_value}')
        
        return '\n'.join(metrics) + '\n'

    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response."""
        response_json = json.dumps(data, indent=2, default=str)
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))

    def _send_error(self, code: int, message: str):
        """Send error response."""
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))


class MetricsServer:
    """
    HTTP server for exposing metrics and health endpoints.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start the metrics server in a background thread."""
        if self._running:
            logger.warning("Metrics server is already running")
            return

        try:
            self.server = HTTPServer((self.host, self.port), MetricsHandler)
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self._running = True
            
            logger.info(f"Metrics server started on http://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    def _run_server(self):
        """Run the HTTP server (called in background thread)."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
        finally:
            self._running = False

    def stop(self):
        """Stop the metrics server."""
        if not self._running:
            return

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
            
            self._running = False
            logger.info("Metrics server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping metrics server: {e}")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running


# Global metrics server instance
_metrics_server: Optional[MetricsServer] = None


def get_metrics_server() -> MetricsServer:
    """Get the global metrics server instance."""
    global _metrics_server
    if _metrics_server is None:
        port = int(os.environ.get("METRICS_PORT", "8000"))
        host = os.environ.get("METRICS_HOST", "0.0.0.0")
        _metrics_server = MetricsServer(host, port)
    return _metrics_server


def start_metrics_server() -> MetricsServer:
    """Start the global metrics server."""
    server = get_metrics_server()
    server.start()
    return server


def stop_metrics_server():
    """Stop the global metrics server."""
    global _metrics_server
    if _metrics_server:
        _metrics_server.stop()
        _metrics_server = None