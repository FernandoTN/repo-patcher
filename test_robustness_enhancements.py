#!/usr/bin/env python3
"""Comprehensive tests for robustness enhancements."""
import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Import our enhancements
from src.repo_patcher.agent.validation import InputValidator, ValidationError
from src.repo_patcher.agent.rate_limiter import (
    SlidingWindowRateLimiter, RateLimitConfig, CircuitBreaker, TokenBucket
)
from src.repo_patcher.agent.structured_logging import (
    get_logger, log_context, operation_timer, metrics
)
from src.repo_patcher.agent.config_schema import (
    validate_agent_config, ConfigValidator, ConfigValidationError
)
from src.repo_patcher.agent.health import HealthChecker, HealthStatus
from src.repo_patcher.agent.shutdown import GracefulShutdown, ResourceManager


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
    
    def test_string_validation_success(self):
        """Test successful string validation."""
        result = self.validator.validate_string("valid_string", "test_field")
        assert result == "valid_string"
    
    def test_string_validation_injection_detection(self):
        """Test injection pattern detection."""
        malicious_inputs = [
            "test; rm -rf /",
            "test && echo 'hacked'",
            "test | cat /etc/passwd",
            "<script>alert('xss')</script>",
            "test`whoami`",
            "../../../etc/passwd",
            "eval('malicious_code')",
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                self.validator.validate_string(malicious_input, "test_field")
    
    def test_path_validation_success(self):
        """Test successful path validation."""
        safe_path = Path("safe/relative/path")
        result = self.validator.validate_path(safe_path)
        assert result == safe_path
    
    def test_path_validation_traversal_detection(self):
        """Test directory traversal detection."""
        dangerous_paths = [
            "../../../etc/passwd",
            "safe/../../../dangerous",
            "/etc/passwd",
            "/usr/bin/dangerous"
        ]
        
        for dangerous_path in dangerous_paths:
            with pytest.raises(ValidationError):
                self.validator.validate_path(dangerous_path)
    
    def test_openai_key_validation(self):
        """Test OpenAI API key validation."""
        # Valid key format
        valid_key = "sk-1234567890abcdef1234567890abcdef"
        result = self.validator.validate_openai_key(valid_key)
        assert result == valid_key
        
        # Invalid key formats
        invalid_keys = [
            "invalid-key",
            "sk-",
            "not-sk-prefix",
            "sk-tooshort"
        ]
        
        for invalid_key in invalid_keys:
            with pytest.raises(ValidationError):
                self.validator.validate_openai_key(invalid_key)
    
    def test_repository_context_validation(self):
        """Test repository context validation."""
        valid_context = {
            "repo_path": "safe/path",
            "repo_url": "https://github.com/user/repo.git",
            "branch": "main",
            "test_framework": "pytest",
            "test_command": "python -m pytest",
            "failing_tests": ["test_file.py::test_function"]
        }
        
        result = self.validator.validate_repository_context(valid_context)
        assert result["repo_path"] == "safe/path"
        assert result["failing_tests"] == ["test_file.py::test_function"]


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=20,
            burst_allowance=3
        )
        return SlidingWindowRateLimiter(config)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self, rate_limiter):
        """Test rate limiter allows requests within limits."""
        # Should allow requests within limits
        for i in range(3):
            allowed = await rate_limiter.acquire()
            assert allowed, f"Request {i+1} should be allowed"
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_requests(self, rate_limiter):
        """Test rate limiter blocks requests exceeding limits."""
        # Fill up the allowance
        for i in range(5):
            await rate_limiter.acquire()
        
        # Next request should be blocked
        blocked = await rate_limiter.acquire()
        assert not blocked, "Request should be blocked after exceeding limit"
    
    def test_token_bucket_functionality(self):
        """Test token bucket implementation."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Should have full capacity initially
        assert bucket.tokens == 5.0
        
        # Should be able to acquire tokens
        import asyncio
        result = asyncio.run(bucket.acquire(3))
        assert result is True
        assert bucket.tokens == 2.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        # Should start in closed state
        assert breaker.state == "closed"
        
        # Simulate failures
        async def failing_function():
            raise Exception("Test failure")
        
        # Should open after failures
        for i in range(3):
            try:
                await breaker.call(failing_function)
            except Exception:
                pass
        
        assert breaker.state == "open"


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_logger_creation(self):
        """Test structured logger creation."""
        logger = get_logger("test_logger")
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
    
    def test_log_context(self):
        """Test logging context management."""
        with log_context(correlation_id="test-123", operation="test-op") as corr_id:
            assert corr_id == "test-123"
            # Context should be active here
    
    @pytest.mark.asyncio
    async def test_operation_timer(self):
        """Test operation timing."""
        logger = get_logger("test")
        
        async with operation_timer(logger, "test_operation", metadata="test") as corr_id:
            await asyncio.sleep(0.01)  # Small delay
            assert corr_id is not None
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        # Reset metrics first
        metrics.reset()
        
        # Test counter
        metrics.increment("test_counter", 5)
        
        # Test gauge
        metrics.gauge("test_gauge", 42.0)
        
        # Test histogram
        metrics.histogram("test_histogram", 1.5)
        
        all_metrics = metrics.get_metrics()
        assert len(all_metrics) >= 3


class TestConfigurationValidation:
    """Test configuration schema validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
    
    def test_valid_agent_config(self):
        """Test validation of valid agent configuration."""
        valid_config = {
            "max_iterations": 3,
            "model_name": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 4000,
            "openai_api_key": "sk-test1234567890abcdef1234567890abcdef"
        }
        
        result = self.validator.validate_config(valid_config, "agent_config")
        assert result["max_iterations"] == 3
        assert result["model_name"] == "gpt-4o-mini"
    
    def test_invalid_agent_config(self):
        """Test validation rejects invalid configuration."""
        invalid_configs = [
            {"max_iterations": -1},  # Below minimum
            {"temperature": 5.0},    # Above maximum
            {"model_name": "invalid-model"},  # Invalid model
            {"openai_api_key": "invalid-key"}  # Invalid key format
        ]
        
        for invalid_config in invalid_configs:
            with pytest.raises(ConfigValidationError):
                self.validator.validate_config(invalid_config, "agent_config")
    
    def test_config_file_validation(self):
        """Test configuration file validation."""
        valid_config = {
            "max_iterations": 5,
            "model_name": "gpt-4o-mini",
            "temperature": 0.2
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config, f)
            config_path = Path(f.name)
        
        try:
            result = self.validator.validate_config_file(config_path, "agent_config")
            assert result["max_iterations"] == 5
        finally:
            config_path.unlink()
    
    def test_default_config_generation(self):
        """Test default configuration generation."""
        default_config = self.validator.generate_default_config("agent_config")
        
        assert "max_iterations" in default_config
        assert "model_name" in default_config
        assert default_config["max_iterations"] == 3
        assert default_config["model_name"] == "gpt-4o-mini"


class TestHealthChecks:
    """Test health check functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for testing."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_memory_check(self, health_checker):
        """Test memory health check."""
        result = await health_checker.run_check("memory")
        
        assert result.name == "memory"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.metadata is not None
        assert "used_percent" in result.metadata
    
    @pytest.mark.asyncio
    async def test_disk_check(self, health_checker):
        """Test disk space health check."""
        result = await health_checker.run_check("disk_space")
        
        assert result.name == "disk_space"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.metadata is not None
        assert "used_percent" in result.metadata
    
    @pytest.mark.asyncio
    async def test_all_health_checks(self, health_checker):
        """Test running all health checks."""
        system_health = await health_checker.run_all_checks()
        
        assert system_health.status is not None
        assert len(system_health.checks) > 0
        assert system_health.summary["total_checks"] == len(system_health.checks)
    
    @pytest.mark.asyncio
    async def test_custom_health_check(self, health_checker):
        """Test custom health check registration."""
        def custom_check():
            return HealthStatus.HEALTHY, "Custom check passed", {"custom": True}
        
        health_checker.register_check("custom", custom_check)
        result = await health_checker.run_check("custom")
        
        assert result.name == "custom"
        assert result.status == HealthStatus.HEALTHY
        assert result.metadata["custom"] is True


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""
    
    @pytest.fixture
    def shutdown_handler(self):
        """Create shutdown handler for testing."""
        return GracefulShutdown(timeout=1.0)  # Short timeout for tests
    
    @pytest.mark.asyncio
    async def test_operation_tracking(self, shutdown_handler):
        """Test operation tracking."""
        async def test_operation():
            async with shutdown_handler.operation("test_op"):
                await asyncio.sleep(0.1)
        
        # Start operation
        task = asyncio.create_task(test_operation())
        await asyncio.sleep(0.05)  # Let it start
        
        # Check that operation is tracked
        assert len(shutdown_handler.active_operations) == 1
        
        # Wait for completion
        await task
        assert len(shutdown_handler.active_operations) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_registration(self, shutdown_handler):
        """Test cleanup function registration."""
        cleanup_called = []
        
        def cleanup_func():
            cleanup_called.append(True)
        
        shutdown_handler.register_cleanup(cleanup_func)
        await shutdown_handler.shutdown()
        
        assert len(cleanup_called) == 1
    
    def test_resource_manager(self):
        """Test resource manager functionality."""
        shutdown_handler = GracefulShutdown()
        resource_manager = ResourceManager(shutdown_handler)
        
        # Mock resource
        mock_resource = MagicMock()
        mock_resource.close = MagicMock()
        
        # Register resource
        resource_manager.register_resource(mock_resource)
        assert len(resource_manager.resources) == 1
        
        # Test cleanup
        asyncio.run(resource_manager.cleanup_all())
        mock_resource.close.assert_called_once()


class TestIntegration:
    """Integration tests for all enhancements."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_robustness(self):
        """Test end-to-end robustness features."""
        # Test input validation
        validator = InputValidator()
        safe_input = validator.validate_string("safe_input", "test")
        assert safe_input == "safe_input"
        
        # Test rate limiting
        rate_limiter = SlidingWindowRateLimiter(RateLimitConfig(
            requests_per_minute=10, requests_per_hour=100
        ))
        allowed = await rate_limiter.acquire()
        assert allowed is True
        
        # Test logging
        logger = get_logger("integration_test")
        with log_context(correlation_id="int-test") as corr_id:
            logger.info("Integration test message")
            assert corr_id == "int-test"
        
        # Test health checks
        health_checker = HealthChecker()
        health = await health_checker.run_all_checks()
        assert health.status is not None
        
        # Test shutdown
        shutdown_handler = GracefulShutdown(timeout=0.1)
        cleanup_called = []
        shutdown_handler.register_cleanup(lambda: cleanup_called.append(True))
        await shutdown_handler.shutdown()
        assert len(cleanup_called) == 1


def main():
    """Run all robustness tests."""
    print("🧪 Running Robustness Enhancement Tests\n")
    
    # Run pytest with verbose output
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")