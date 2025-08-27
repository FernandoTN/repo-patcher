"""Rate limiting for external API calls."""
import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    burst_allowance: int = 10
    cooldown_period: float = 1.0


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens_needed: int = 1) -> bool:
        """
        Try to acquire tokens from bucket.
        
        Args:
            tokens_needed: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            now = time.time()
            time_passed = now - self.last_refill
            
            # Refill tokens based on time passed
            tokens_to_add = time_passed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens_needed: int = 1, max_wait: float = 60.0) -> bool:
        """
        Wait until tokens are available.
        
        Args:
            tokens_needed: Number of tokens needed
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if tokens were acquired, False if timed out
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire(tokens_needed):
                return True
            
            # Calculate optimal wait time
            async with self._lock:
                if self.tokens < tokens_needed:
                    tokens_deficit = tokens_needed - self.tokens
                    wait_time = min(tokens_deficit / self.refill_rate, 1.0)
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(0.1)
        
        return False


class SlidingWindowRateLimiter:
    """Sliding window rate limiter with multiple time windows."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter with configuration."""
        self.config = config
        self.minute_window = deque()
        self.hour_window = deque()
        self.burst_bucket = TokenBucket(
            capacity=config.burst_allowance,
            refill_rate=config.burst_allowance / 60.0  # Refill burst allowance over 1 minute
        )
        self._lock = asyncio.Lock()
    
    async def acquire(self, weight: int = 1) -> bool:
        """
        Try to acquire permission for a request.
        
        Args:
            weight: Weight of the request (default 1)
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        
        async with self._lock:
            # Clean old entries
            self._clean_windows(now)
            
            # Check rate limits
            if len(self.minute_window) + weight > self.config.requests_per_minute:
                logger.debug("Request blocked: minute rate limit exceeded")
                return False
            
            if len(self.hour_window) + weight > self.config.requests_per_hour:
                logger.debug("Request blocked: hourly rate limit exceeded")
                return False
            
            # Check burst allowance
            if not await self.burst_bucket.acquire(weight):
                logger.debug("Request blocked: burst limit exceeded")
                return False
            
            # Add requests to windows
            for _ in range(weight):
                self.minute_window.append(now)
                self.hour_window.append(now)
            
            return True
    
    async def wait_for_slot(self, weight: int = 1, max_wait: float = 300.0) -> bool:
        """
        Wait for a slot to become available.
        
        Args:
            weight: Weight of the request
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if slot acquired, False if timed out
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire(weight):
                return True
            
            # Calculate wait time based on next available slot
            wait_time = await self._calculate_wait_time(weight)
            await asyncio.sleep(min(wait_time, 1.0))
        
        return False
    
    async def _calculate_wait_time(self, weight: int) -> float:
        """Calculate optimal wait time for next request."""
        now = time.time()
        
        async with self._lock:
            # Check when minute window will have space
            minute_wait = 0.0
            if len(self.minute_window) + weight > self.config.requests_per_minute:
                # Wait until oldest requests in minute window expire
                needed_slots = (len(self.minute_window) + weight) - self.config.requests_per_minute
                if needed_slots <= len(self.minute_window):
                    minute_wait = max(0, 60.0 - (now - self.minute_window[needed_slots - 1]))
            
            # Check when hour window will have space
            hour_wait = 0.0
            if len(self.hour_window) + weight > self.config.requests_per_hour:
                needed_slots = (len(self.hour_window) + weight) - self.config.requests_per_hour
                if needed_slots <= len(self.hour_window):
                    hour_wait = max(0, 3600.0 - (now - self.hour_window[needed_slots - 1]))
            
            return max(minute_wait, hour_wait, self.config.cooldown_period)
    
    def _clean_windows(self, now: float) -> None:
        """Remove expired entries from sliding windows."""
        # Clean minute window (60 seconds)
        while self.minute_window and now - self.minute_window[0] >= 60.0:
            self.minute_window.popleft()
        
        # Clean hour window (3600 seconds)
        while self.hour_window and now - self.hour_window[0] >= 3600.0:
            self.hour_window.popleft()
    
    def get_status(self) -> Dict[str, any]:
        """Get current rate limiter status."""
        now = time.time()
        self._clean_windows(now)
        
        return {
            "requests_last_minute": len(self.minute_window),
            "requests_last_hour": len(self.hour_window),
            "minute_limit": self.config.requests_per_minute,
            "hour_limit": self.config.requests_per_hour,
            "burst_tokens_available": self.burst_bucket.tokens,
            "burst_capacity": self.burst_bucket.capacity
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                 success_threshold: int = 3):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying to close circuit
            success_threshold: Number of successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: When circuit is open
        """
        async with self._lock:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                    logger.info("Circuit breaker attempting recovery")
                else:
                    raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        
        except Exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self.failure_count = 0
            
            if self.state == "half-open":
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = "closed"
                    self.success_count = 0
                    logger.info("Circuit breaker closed after recovery")
    
    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.success_count = 0
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, any]:
        """Get current circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class CircuitBreakerError(Exception):
    """Circuit breaker is open."""
    pass


# Global instances for different services
openai_rate_limiter = SlidingWindowRateLimiter(RateLimitConfig(
    requests_per_minute=60,    # Conservative OpenAI limit
    requests_per_hour=3600,
    burst_allowance=10,
    cooldown_period=1.0
))

openai_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2
)