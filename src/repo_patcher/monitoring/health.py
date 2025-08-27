"""
Health monitoring and status reporting for Repo Patcher.

This module provides comprehensive health checks including:
- System resource monitoring (CPU, memory, disk)
- API connectivity and rate limit status
- Agent component health
- Performance metrics and thresholds
"""

import os
import time
import logging
import asyncio
import psutil
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    description: str
    check_func: Callable[[], Dict[str, Any]]
    critical: bool = False  # Whether this check failing means the system is unhealthy
    timeout: int = 10  # Timeout in seconds


@dataclass
class HealthReport:
    """Comprehensive health report."""
    status: HealthStatus
    timestamp: float
    checks: Dict[str, Dict[str, Any]]
    summary: str
    uptime: float
    version: str = "0.1.0"


class HealthMonitor:
    """
    Monitors system health and provides status reports for Repo Patcher.
    """

    def __init__(self):
        self.start_time = time.time()
        self.checks: Dict[str, HealthCheck] = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks."""
        
        # System resource checks
        self.register_check(HealthCheck(
            name="cpu_usage",
            description="CPU usage percentage",
            check_func=self._check_cpu_usage,
            critical=False
        ))
        
        self.register_check(HealthCheck(
            name="memory_usage",
            description="Memory usage percentage",
            check_func=self._check_memory_usage,
            critical=True
        ))
        
        self.register_check(HealthCheck(
            name="disk_usage",
            description="Disk usage percentage",
            check_func=self._check_disk_usage,
            critical=False
        ))
        
        # Application-specific checks
        self.register_check(HealthCheck(
            name="openai_connectivity",
            description="OpenAI API connectivity",
            check_func=self._check_openai_connectivity,
            critical=True
        ))
        
        self.register_check(HealthCheck(
            name="git_availability",
            description="Git command availability",
            check_func=self._check_git_availability,
            critical=True
        ))
        
        self.register_check(HealthCheck(
            name="workspace_access",
            description="Workspace directory access",
            check_func=self._check_workspace_access,
            critical=True
        ))

    def register_check(self, health_check: HealthCheck):
        """Register a new health check."""
        self.checks[health_check.name] = health_check
        logger.debug(f"Registered health check: {health_check.name}")

    def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            status = HealthStatus.HEALTHY
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70:
                status = HealthStatus.DEGRADED
            
            return {
                "status": status.value,
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e)
            }

    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            status = HealthStatus.HEALTHY
            
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
            
            return {
                "status": status.value,
                "memory_percent": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_used": memory.used
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e)
            }

    def _check_disk_usage(self) -> Dict[str, Any]:
        """Check disk usage."""
        try:
            disk = psutil.disk_usage('/')
            status = HealthStatus.HEALTHY
            
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
            
            return {
                "status": status.value,
                "disk_percent": usage_percent,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "disk_free": disk.free
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e)
            }

    def _check_openai_connectivity(self) -> Dict[str, Any]:
        """Check OpenAI API connectivity."""
        try:
            # Check if API key is available
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": "OPENAI_API_KEY not configured"
                }
            
            # Basic API key format validation
            if not api_key.startswith("sk-"):
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "warning": "API key format may be invalid"
                }
            
            # TODO: Add actual API connectivity test with timeout
            # For now, just check key presence and format
            return {
                "status": HealthStatus.HEALTHY.value,
                "api_key_present": True,
                "api_key_format_valid": True
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e)
            }

    def _check_git_availability(self) -> Dict[str, Any]:
        """Check Git command availability."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "git_version": result.stdout.strip(),
                    "available": True
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": "Git command failed",
                    "available": False
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": HealthStatus.DEGRADED.value,
                "error": "Git command timeout",
                "available": False
            }
        except FileNotFoundError:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": "Git not installed",
                "available": False
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e),
                "available": False
            }

    def _check_workspace_access(self) -> Dict[str, Any]:
        """Check workspace directory access."""
        try:
            workspace_path = os.environ.get("WORKSPACE_PATH", "/workspace")
            
            # Check if directory exists and is writable
            if not os.path.exists(workspace_path):
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": f"Workspace directory does not exist: {workspace_path}",
                    "path": workspace_path
                }
            
            if not os.access(workspace_path, os.W_OK):
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": f"Workspace directory not writable: {workspace_path}",
                    "path": workspace_path
                }
            
            # Check available space
            try:
                stat = os.statvfs(workspace_path)
                available_bytes = stat.f_bavail * stat.f_frsize
                available_gb = available_bytes / (1024**3)
                
                if available_gb < 0.1:  # Less than 100MB
                    return {
                        "status": HealthStatus.UNHEALTHY.value,
                        "error": "Insufficient workspace storage",
                        "path": workspace_path,
                        "available_gb": available_gb
                    }
                elif available_gb < 1.0:  # Less than 1GB
                    return {
                        "status": HealthStatus.DEGRADED.value,
                        "warning": "Low workspace storage",
                        "path": workspace_path,
                        "available_gb": available_gb
                    }
                
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "path": workspace_path,
                    "available_gb": available_gb,
                    "writable": True
                }
                
            except (OSError, AttributeError):
                # statvfs not available on all systems
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "path": workspace_path,
                    "writable": True,
                    "space_check": "unavailable"
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e)
            }

    def run_check(self, check_name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if check_name not in self.checks:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Unknown health check: {check_name}"
            }
        
        check = self.checks[check_name]
        
        try:
            # Run check with timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Health check '{check_name}' timed out")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(check.timeout)
            
            try:
                result = check.check_func()
                result["check_name"] = check_name
                result["description"] = check.description
                result["critical"] = check.critical
                return result
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                
        except TimeoutError as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e),
                "check_name": check_name,
                "critical": check.critical
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Health check failed: {str(e)}",
                "check_name": check_name,
                "critical": check.critical
            }

    def get_health_report(self) -> HealthReport:
        """Generate comprehensive health report."""
        check_results = {}
        overall_status = HealthStatus.HEALTHY
        
        # Run all health checks
        for check_name in self.checks:
            result = self.run_check(check_name)
            check_results[check_name] = result
            
            # Determine overall status
            check_status = HealthStatus(result.get("status", "unknown"))
            
            if self.checks[check_name].critical:
                if check_status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check_status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                elif check_status == HealthStatus.UNKNOWN and overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                    overall_status = HealthStatus.DEGRADED
        
        # Generate summary
        healthy_count = sum(1 for r in check_results.values() if r.get("status") == "healthy")
        total_count = len(check_results)
        uptime = time.time() - self.start_time
        
        summary = f"{healthy_count}/{total_count} checks passing, uptime: {uptime:.1f}s"
        
        return HealthReport(
            status=overall_status,
            timestamp=time.time(),
            checks=check_results,
            summary=summary,
            uptime=uptime
        )

    def is_healthy(self) -> bool:
        """Quick health check - returns True if system is healthy."""
        report = self.get_health_report()
        return report.status == HealthStatus.HEALTHY


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def get_health_report() -> HealthReport:
    """Get current health report."""
    return get_health_monitor().get_health_report()


def is_healthy() -> bool:
    """Quick health check."""
    return get_health_monitor().is_healthy()