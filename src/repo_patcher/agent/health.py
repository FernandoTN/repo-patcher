"""Health checks and monitoring for the agent."""
import time
import asyncio
import psutil
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .structured_logging import get_logger, metrics
from .rate_limiter import openai_rate_limiter, openai_circuit_breaker


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: float
    checks: List[HealthCheck]
    summary: Dict[str, Any]


class HealthChecker:
    """System health checker."""
    
    def __init__(self):
        """Initialize health checker."""
        self.logger = get_logger(__name__)
        self.checks: Dict[str, Callable] = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("memory", self._check_memory)
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("rate_limiter", self._check_rate_limiter)
        self.register_check("circuit_breaker", self._check_circuit_breaker)
        self.register_check("metrics", self._check_metrics)
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def run_check(self, name: str) -> HealthCheck:
        """Run a single health check."""
        if name not in self.checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found",
                duration_ms=0.0
            )
        
        start_time = time.time()
        try:
            check_func = self.checks[name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheck):
                result.duration_ms = duration_ms
                return result
            elif isinstance(result, tuple):
                status, message, metadata = result if len(result) == 3 else (*result, None)
                return HealthCheck(
                    name=name,
                    status=status,
                    message=message,
                    duration_ms=duration_ms,
                    metadata=metadata
                )
            else:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="Check passed",
                    duration_ms=duration_ms
                )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check '{name}' failed", error=str(e))
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    async def run_all_checks(self) -> SystemHealth:
        """Run all registered health checks."""
        start_time = time.time()
        
        # Run all checks concurrently
        check_tasks = [self.run_check(name) for name in self.checks.keys()]
        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        checks = []
        for result in check_results:
            if isinstance(result, Exception):
                checks.append(HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed with exception: {result}",
                    duration_ms=0.0
                ))
            else:
                checks.append(result)
        
        # Determine overall health status
        overall_status = self._determine_overall_status(checks)
        
        # Build summary
        summary = {
            "total_checks": len(checks),
            "healthy_checks": len([c for c in checks if c.status == HealthStatus.HEALTHY]),
            "degraded_checks": len([c for c in checks if c.status == HealthStatus.DEGRADED]),
            "unhealthy_checks": len([c for c in checks if c.status == HealthStatus.UNHEALTHY]),
            "total_duration_ms": (time.time() - start_time) * 1000
        }
        
        return SystemHealth(
            status=overall_status,
            timestamp=time.time(),
            checks=checks,
            summary=summary
        )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = len([c for c in checks if c.status == HealthStatus.UNHEALTHY])
        degraded_count = len([c for c in checks if c.status == HealthStatus.DEGRADED])
        
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    # Default health check implementations
    
    def _check_memory(self) -> tuple:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            
            metadata = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory_usage_percent
            }
            
            if memory_usage_percent > 90:
                return HealthStatus.UNHEALTHY, f"Memory usage critical: {memory_usage_percent}%", metadata
            elif memory_usage_percent > 80:
                return HealthStatus.DEGRADED, f"Memory usage high: {memory_usage_percent}%", metadata
            else:
                return HealthStatus.HEALTHY, f"Memory usage normal: {memory_usage_percent}%", metadata
        
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Cannot check memory: {e}", None
    
    def _check_disk_space(self) -> tuple:
        """Check disk space usage."""
        try:
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            metadata = {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": round(disk_usage_percent, 2)
            }
            
            if disk_usage_percent > 95:
                return HealthStatus.UNHEALTHY, f"Disk usage critical: {disk_usage_percent:.1f}%", metadata
            elif disk_usage_percent > 85:
                return HealthStatus.DEGRADED, f"Disk usage high: {disk_usage_percent:.1f}%", metadata
            else:
                return HealthStatus.HEALTHY, f"Disk usage normal: {disk_usage_percent:.1f}%", metadata
        
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Cannot check disk space: {e}", None
    
    def _check_rate_limiter(self) -> tuple:
        """Check rate limiter status."""
        try:
            status = openai_rate_limiter.get_status()
            
            minute_usage = status["requests_last_minute"] / status["minute_limit"]
            hour_usage = status["requests_last_hour"] / status["hour_limit"]
            
            metadata = {
                "requests_last_minute": status["requests_last_minute"],
                "minute_limit": status["minute_limit"],
                "minute_usage_percent": round(minute_usage * 100, 1),
                "requests_last_hour": status["requests_last_hour"],
                "hour_limit": status["hour_limit"],
                "hour_usage_percent": round(hour_usage * 100, 1),
                "burst_tokens": round(status["burst_tokens_available"], 1)
            }
            
            if minute_usage > 0.9 or hour_usage > 0.9:
                return HealthStatus.DEGRADED, "Rate limits approaching", metadata
            else:
                return HealthStatus.HEALTHY, "Rate limiter functioning normally", metadata
        
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Cannot check rate limiter: {e}", None
    
    def _check_circuit_breaker(self) -> tuple:
        """Check circuit breaker status."""
        try:
            status = openai_circuit_breaker.get_status()
            
            metadata = {
                "state": status["state"],
                "failure_count": status["failure_count"],
                "success_count": status["success_count"],
                "last_failure_time": status["last_failure_time"]
            }
            
            if status["state"] == "open":
                return HealthStatus.UNHEALTHY, "Circuit breaker is open", metadata
            elif status["state"] == "half-open":
                return HealthStatus.DEGRADED, "Circuit breaker is half-open", metadata
            else:
                return HealthStatus.HEALTHY, "Circuit breaker is closed", metadata
        
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Cannot check circuit breaker: {e}", None
    
    def _check_metrics(self) -> tuple:
        """Check metrics collection."""
        try:
            current_metrics = metrics.get_metrics()
            
            metadata = {
                "total_metrics": len(current_metrics),
                "metric_types": list(set(m.get("type", "unknown") for m in current_metrics.values()))
            }
            
            if len(current_metrics) == 0:
                return HealthStatus.DEGRADED, "No metrics collected yet", metadata
            else:
                return HealthStatus.HEALTHY, f"Metrics collection active: {len(current_metrics)} metrics", metadata
        
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Cannot check metrics: {e}", None


class HealthMonitor:
    """Periodic health monitoring."""
    
    def __init__(self, checker: HealthChecker, check_interval: float = 60.0):
        """Initialize health monitor."""
        self.checker = checker
        self.check_interval = check_interval
        self.logger = get_logger(__name__)
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    def start(self) -> None:
        """Start periodic health monitoring."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started", interval=self.check_interval)
    
    def stop(self) -> None:
        """Stop periodic health monitoring."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                health = await self.checker.run_all_checks()
                
                # Log health status
                self._log_health_status(health)
                
                # Update metrics
                self._update_health_metrics(health)
                
                # Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health monitoring loop", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    def _log_health_status(self, health: SystemHealth) -> None:
        """Log health status."""
        if health.status == HealthStatus.HEALTHY:
            self.logger.info("System health check passed", 
                           status=health.status.value,
                           checks=health.summary["total_checks"],
                           duration_ms=round(health.summary["total_duration_ms"], 2))
        else:
            failed_checks = [c.name for c in health.checks if c.status != HealthStatus.HEALTHY]
            self.logger.warning("System health issues detected",
                              status=health.status.value,
                              failed_checks=failed_checks,
                              checks=health.summary["total_checks"])
    
    def _update_health_metrics(self, health: SystemHealth) -> None:
        """Update health metrics."""
        # Overall health status
        status_values = {
            HealthStatus.HEALTHY: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.UNHEALTHY: 3,
            HealthStatus.UNKNOWN: 0
        }
        metrics.gauge("system_health_status", status_values[health.status])
        
        # Individual check statuses
        for check in health.checks:
            metrics.gauge(f"health_check_status", status_values[check.status], 
                         {"check_name": check.name})
            metrics.histogram(f"health_check_duration", check.duration_ms / 1000, 
                            {"check_name": check.name})


# Global health checker and monitor
health_checker = HealthChecker()
health_monitor = HealthMonitor(health_checker)


def get_health_status() -> SystemHealth:
    """Get current health status (synchronous)."""
    return asyncio.run(health_checker.run_all_checks())


async def get_health_status_async() -> SystemHealth:
    """Get current health status (asynchronous)."""
    return await health_checker.run_all_checks()