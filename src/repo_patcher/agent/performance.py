"""Performance optimization and cost efficiency features."""
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from .models import AgentSession, StepExecution


class OptimizationLevel(Enum):
    """Performance optimization levels."""
    CONSERVATIVE = "conservative"  # Prioritize accuracy over speed
    BALANCED = "balanced"         # Balance speed and accuracy
    AGGRESSIVE = "aggressive"     # Prioritize speed over accuracy


class CacheType(Enum):
    """Types of cached data."""
    REPOSITORY_ANALYSIS = "repo_analysis"
    TEST_OUTPUT = "test_output"
    CODE_SEARCH = "code_search"
    AI_RESPONSE = "ai_response"
    LANGUAGE_DETECTION = "language_detection"


@dataclass
class CacheEntry:
    """Represents a cached computation result."""
    key: str
    value: Any
    timestamp: float
    access_count: int = 0
    ttl: float = 3600  # 1 hour default TTL
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def access(self) -> Any:
        """Access the cached value and update access count."""
        self.access_count += 1
        return self.value


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization tracking."""
    total_execution_time: float = 0.0
    ai_api_calls: int = 0
    ai_api_cost: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_used: int = 0
    repository_analysis_time: float = 0.0
    test_execution_time: float = 0.0
    patch_generation_time: float = 0.0
    
    @property
    def cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def cost_per_fix_attempt(self) -> float:
        """Calculate cost per fix attempt."""
        return self.ai_api_cost / max(1, self.ai_api_calls)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_execution_time": self.total_execution_time,
            "ai_api_calls": self.ai_api_calls,
            "ai_api_cost": self.ai_api_cost,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": self.cache_hit_ratio,
            "tokens_used": self.tokens_used,
            "cost_per_fix_attempt": self.cost_per_fix_attempt,
            "repository_analysis_time": self.repository_analysis_time,
            "test_execution_time": self.test_execution_time,
            "patch_generation_time": self.patch_generation_time
        }


class IntelligentCache:
    """Intelligent caching system with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """Generate a cache key from data."""
        data_str = str(data)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()[:16]}"
    
    def get(self, cache_type: CacheType, data: Any) -> Optional[Any]:
        """Get value from cache."""
        key = self._generate_key(cache_type.value, data)
        
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired:
            self._remove_key(key)
            return None
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry.access()
    
    def set(self, cache_type: CacheType, data: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        key = self._generate_key(cache_type.value, data)
        
        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )
        
        self._cache[key] = entry
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            self._remove_key(lru_key)
    
    def _remove_key(self, key: str) -> None:
        """Remove key from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear_expired(self) -> int:
        """Clear expired entries and return count cleared."""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_key(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_access = sum(entry.access_count for entry in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_accesses": total_access,
            "expired_entries": sum(1 for entry in self._cache.values() if entry.is_expired)
        }


class CostOptimizer:
    """AI API cost optimization strategies."""
    
    def __init__(self):
        self.cost_targets = {
            "max_cost_per_session": 0.50,
            "max_cost_per_fix": 0.25,
            "warning_threshold": 0.75  # Warn at 75% of target
        }
        self.model_costs = {
            "gpt-4o": {"input": 0.005, "output": 0.015},  # Per 1K tokens
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for AI API call."""
        if model not in self.model_costs:
            model = "gpt-4o-mini"  # Default to cheapest model
        
        costs = self.model_costs[model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def recommend_model(self, task_complexity: str, current_cost: float, budget_remaining: float) -> str:
        """Recommend optimal model based on complexity and budget."""
        
        # If budget is tight, use cheapest model
        if budget_remaining < 0.10:
            return "gpt-4o-mini"
        
        # For simple tasks, use cost-effective model
        if task_complexity in ["simple", "low"]:
            return "gpt-4o-mini"
        
        # For complex tasks with sufficient budget, use more capable model
        if task_complexity in ["complex", "high"] and budget_remaining > 0.25:
            return "gpt-4o"
        
        # Default to balanced model
        return "gpt-4o-mini"
    
    def should_use_cache(self, cache_type: CacheType, estimated_cost: float) -> bool:
        """Determine if caching should be used for a given operation."""
        
        # Always cache expensive operations
        if estimated_cost > 0.05:
            return True
        
        # Cache repository analysis (expensive computation)
        if cache_type == CacheType.REPOSITORY_ANALYSIS:
            return True
        
        # Cache AI responses for reuse
        if cache_type == CacheType.AI_RESPONSE and estimated_cost > 0.01:
            return True
        
        return False
    
    def optimize_prompt(self, prompt: str, max_tokens: int) -> str:
        """Optimize prompt for cost efficiency while maintaining effectiveness."""
        
        # Remove excessive whitespace
        optimized = " ".join(prompt.split())
        
        # Truncate if too long
        if len(optimized.split()) > max_tokens * 0.75:  # Rough word-to-token ratio
            words = optimized.split()
            truncated_words = words[:int(max_tokens * 0.75)]
            optimized = " ".join(truncated_words) + "..."
        
        return optimized


class PerformanceOptimizer:
    """Main performance optimization system."""
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.BALANCED):
        self.optimization_level = optimization_level
        self.cache = IntelligentCache()
        self.cost_optimizer = CostOptimizer()
        self.metrics = PerformanceMetrics()
        self._session_start_times: Dict[str, float] = {}
    
    def start_session_timing(self, session_id: str) -> None:
        """Start timing a session."""
        self._session_start_times[session_id] = time.time()
    
    def end_session_timing(self, session_id: str) -> float:
        """End timing a session and return duration."""
        start_time = self._session_start_times.get(session_id)
        if start_time:
            duration = time.time() - start_time
            self.metrics.total_execution_time += duration
            del self._session_start_times[session_id]
            return duration
        return 0.0
    
    def should_use_cache(self, cache_type: CacheType, data: Any, estimated_cost: float = 0.0) -> bool:
        """Determine if caching should be used."""
        
        # Always use cache in aggressive mode
        if self.optimization_level == OptimizationLevel.AGGRESSIVE:
            return True
        
        # Use cost-based decision in balanced mode
        if self.optimization_level == OptimizationLevel.BALANCED:
            return self.cost_optimizer.should_use_cache(cache_type, estimated_cost)
        
        # Conservative mode: only cache expensive operations
        if self.optimization_level == OptimizationLevel.CONSERVATIVE:
            return cache_type in [CacheType.REPOSITORY_ANALYSIS, CacheType.AI_RESPONSE] and estimated_cost > 0.02
        
        return False
    
    def get_from_cache(self, cache_type: CacheType, data: Any) -> Optional[Any]:
        """Get data from cache and update metrics."""
        result = self.cache.get(cache_type, data)
        if result is not None:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1
        return result
    
    def set_cache(self, cache_type: CacheType, data: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Set data in cache."""
        self.cache.set(cache_type, data, value, ttl)
    
    def record_ai_call(self, model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        """Record AI API call metrics."""
        self.metrics.ai_api_calls += 1
        self.metrics.ai_api_cost += cost
        self.metrics.tokens_used += input_tokens + output_tokens
    
    def recommend_optimization_strategy(self, session: AgentSession) -> Dict[str, Any]:
        """Recommend optimization strategies based on current performance."""
        recommendations = []
        
        # Cost-based recommendations
        if session.total_cost > session.config.max_cost_per_session * 0.75:
            recommendations.append({
                "type": "cost_warning",
                "message": f"Approaching cost limit: ${session.total_cost:.3f} / ${session.config.max_cost_per_session}",
                "action": "Consider using cheaper model or increasing cache usage"
            })
        
        # Time-based recommendations
        if session.duration > session.config.max_session_duration * 0.75:
            recommendations.append({
                "type": "time_warning",
                "message": f"Approaching time limit: {session.duration:.1f}s / {session.config.max_session_duration}s",
                "action": "Consider simplifying approach or setting shorter timeouts"
            })
        
        # Cache efficiency recommendations
        if self.metrics.cache_hit_ratio < 0.3:
            recommendations.append({
                "type": "cache_efficiency",
                "message": f"Low cache hit ratio: {self.metrics.cache_hit_ratio:.1%}",
                "action": "Consider increasing cache TTL or cache more operations"
            })
        
        # Model selection recommendations
        avg_cost = self.metrics.cost_per_fix_attempt
        if avg_cost > 0.15:
            recommendations.append({
                "type": "model_optimization",
                "message": f"High average cost per attempt: ${avg_cost:.3f}",
                "action": "Consider using gpt-4o-mini for simpler tasks"
            })
        
        return {
            "recommendations": recommendations,
            "current_metrics": self.metrics.to_dict(),
            "optimization_level": self.optimization_level.value
        }
    
    def get_optimization_settings(self, task_complexity: str, current_session: AgentSession) -> Dict[str, Any]:
        """Get optimized settings for current task."""
        
        budget_remaining = current_session.config.max_cost_per_session - current_session.total_cost
        model = self.cost_optimizer.recommend_model(task_complexity, current_session.total_cost, budget_remaining)
        
        settings = {
            "model": model,
            "max_tokens": 1000,
            "temperature": 0.1,
            "use_cache": True,
            "cache_ttl": 3600
        }
        
        # Adjust based on optimization level
        if self.optimization_level == OptimizationLevel.AGGRESSIVE:
            settings.update({
                "max_tokens": 800,
                "temperature": 0.0,  # More deterministic
                "cache_ttl": 7200   # Longer cache
            })
        elif self.optimization_level == OptimizationLevel.CONSERVATIVE:
            settings.update({
                "max_tokens": 1500,
                "temperature": 0.2,  # More creative
                "cache_ttl": 1800   # Shorter cache
            })
        
        return settings
    
    def cleanup_cache(self) -> Dict[str, int]:
        """Clean up expired cache entries."""
        expired_count = self.cache.clear_expired()
        return {
            "expired_entries_removed": expired_count,
            "current_cache_size": len(self.cache._cache)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "metrics": self.metrics.to_dict(),
            "cache_stats": self.cache.get_stats(),
            "optimization_level": self.optimization_level.value,
            "active_sessions": len(self._session_start_times)
        }