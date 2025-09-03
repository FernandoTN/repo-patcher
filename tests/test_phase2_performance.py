"""Tests for Phase 2 performance optimization features."""
import pytest
import time
from unittest.mock import Mock, patch

from src.repo_patcher.agent.performance import (
    IntelligentCache, CostOptimizer, PerformanceOptimizer,
    CacheType, OptimizationLevel, PerformanceMetrics, CacheEntry
)
from src.repo_patcher.agent.models import AgentSession, RepositoryContext, AgentConfig
from src.repo_patcher.agent.config import AgentConfig


class TestCacheEntry:
    """Test cache entry functionality."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            timestamp=time.time(),
            ttl=3600
        )
        
        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.access_count == 0
        assert not entry.is_expired
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        
        assert entry.is_expired
    
    def test_cache_entry_access(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time(),
            ttl=3600
        )
        
        # Access the entry
        value = entry.access()
        
        assert value == "test_value"
        assert entry.access_count == 1
        
        # Access again
        entry.access()
        assert entry.access_count == 2


class TestIntelligentCache:
    """Test the intelligent caching system."""
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = IntelligentCache(max_size=10)
        
        # Set a value
        cache.set(CacheType.REPOSITORY_ANALYSIS, "repo_path", {"analysis": "data"})
        
        # Get the value
        result = cache.get(CacheType.REPOSITORY_ANALYSIS, "repo_path")
        
        assert result == {"analysis": "data"}
    
    def test_cache_miss(self):
        """Test cache miss scenario."""
        cache = IntelligentCache(max_size=10)
        
        # Try to get non-existent value
        result = cache.get(CacheType.AI_RESPONSE, "non_existent_key")
        
        assert result is None
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = IntelligentCache(max_size=10, default_ttl=0.1)  # 0.1 second TTL
        
        # Set a value
        cache.set(CacheType.CODE_SEARCH, "search_query", ["result1", "result2"])
        
        # Immediately get - should work
        result = cache.get(CacheType.CODE_SEARCH, "search_query")
        assert result == ["result1", "result2"]
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        result = cache.get(CacheType.CODE_SEARCH, "search_query")
        assert result is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = IntelligentCache(max_size=2)  # Very small cache
        
        # Fill the cache
        cache.set(CacheType.REPOSITORY_ANALYSIS, "repo1", "data1")
        cache.set(CacheType.REPOSITORY_ANALYSIS, "repo2", "data2")
        
        # Access first item to make it recently used
        cache.get(CacheType.REPOSITORY_ANALYSIS, "repo1")
        
        # Add third item - should evict repo2 (least recently used)
        cache.set(CacheType.REPOSITORY_ANALYSIS, "repo3", "data3")
        
        # repo1 should still be there (recently accessed)
        assert cache.get(CacheType.REPOSITORY_ANALYSIS, "repo1") == "data1"
        
        # repo2 should be evicted
        assert cache.get(CacheType.REPOSITORY_ANALYSIS, "repo2") is None
        
        # repo3 should be there (newly added)
        assert cache.get(CacheType.REPOSITORY_ANALYSIS, "repo3") == "data3"
    
    def test_cache_clear_expired(self):
        """Test clearing expired entries."""
        cache = IntelligentCache(max_size=10, default_ttl=0.1)
        
        # Add some entries
        cache.set(CacheType.TEST_OUTPUT, "test1", "result1")
        cache.set(CacheType.TEST_OUTPUT, "test2", "result2")
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Clear expired entries
        cleared_count = cache.clear_expired()
        
        assert cleared_count == 2
        assert len(cache._cache) == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = IntelligentCache(max_size=10)
        
        # Add some entries and access them
        cache.set(CacheType.LANGUAGE_DETECTION, "repo1", "python")
        cache.get(CacheType.LANGUAGE_DETECTION, "repo1")
        cache.get(CacheType.LANGUAGE_DETECTION, "repo1")
        
        stats = cache.get_stats()
        
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["total_accesses"] == 2


class TestCostOptimizer:
    """Test the cost optimization functionality."""
    
    def test_estimate_cost(self):
        """Test cost estimation for different models."""
        optimizer = CostOptimizer()
        
        # Test GPT-4o cost
        cost = optimizer.estimate_cost("gpt-4o", 1000, 500)  # 1k input, 500 output tokens
        expected = (1000/1000 * 0.005) + (500/1000 * 0.015)  # Input + output cost
        assert abs(cost - expected) < 0.001
        
        # Test GPT-4o-mini cost (cheaper)
        cost_mini = optimizer.estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost_mini < cost  # Should be cheaper
    
    def test_recommend_model_budget_constrained(self):
        """Test model recommendation when budget is tight."""
        optimizer = CostOptimizer()
        
        # Low budget remaining
        model = optimizer.recommend_model("complex", current_cost=0.45, budget_remaining=0.05)
        assert model == "gpt-4o-mini"  # Should recommend cheapest model
    
    def test_recommend_model_simple_task(self):
        """Test model recommendation for simple tasks."""
        optimizer = CostOptimizer()
        
        model = optimizer.recommend_model("simple", current_cost=0.10, budget_remaining=0.40)
        assert model == "gpt-4o-mini"  # Should use cost-effective model for simple tasks
    
    def test_recommend_model_complex_task(self):
        """Test model recommendation for complex tasks with sufficient budget."""
        optimizer = CostOptimizer()
        
        model = optimizer.recommend_model("complex", current_cost=0.10, budget_remaining=0.35)
        assert model == "gpt-4o"  # Should use more capable model for complex tasks
    
    def test_should_use_cache(self):
        """Test cache usage recommendations."""
        optimizer = CostOptimizer()
        
        # Expensive operation should be cached
        assert optimizer.should_use_cache(CacheType.AI_RESPONSE, estimated_cost=0.10)
        
        # Repository analysis should always be cached
        assert optimizer.should_use_cache(CacheType.REPOSITORY_ANALYSIS, estimated_cost=0.01)
        
        # Cheap operations might not need caching
        assert not optimizer.should_use_cache(CacheType.CODE_SEARCH, estimated_cost=0.005)
    
    def test_optimize_prompt(self):
        """Test prompt optimization for cost efficiency."""
        optimizer = CostOptimizer()
        
        # Test whitespace removal
        prompt = "This   is   a   test   prompt   with   extra   whitespace"
        optimized = optimizer.optimize_prompt(prompt, max_tokens=1000)
        assert "  " not in optimized  # Should remove extra whitespace
        
        # Test truncation for long prompts
        long_prompt = " ".join(["word"] * 1000)  # Very long prompt
        optimized = optimizer.optimize_prompt(long_prompt, max_tokens=100)
        assert len(optimized.split()) < 100  # Should be truncated
        assert optimized.endswith("...")


class TestPerformanceMetrics:
    """Test performance metrics tracking."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = PerformanceMetrics()
        
        assert metrics.total_execution_time == 0.0
        assert metrics.ai_api_calls == 0
        assert metrics.ai_api_cost == 0.0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
    
    def test_cache_hit_ratio_calculation(self):
        """Test cache hit ratio calculation."""
        metrics = PerformanceMetrics()
        
        # No requests yet
        assert metrics.cache_hit_ratio == 0.0
        
        # Add some cache activity
        metrics.cache_hits = 7
        metrics.cache_misses = 3
        
        assert metrics.cache_hit_ratio == 0.7  # 7/10
    
    def test_cost_per_fix_calculation(self):
        """Test cost per fix attempt calculation."""
        metrics = PerformanceMetrics()
        
        # No API calls yet
        assert metrics.cost_per_fix_attempt == 0.0
        
        # Add API activity
        metrics.ai_api_calls = 5
        metrics.ai_api_cost = 1.25
        
        assert metrics.cost_per_fix_attempt == 0.25  # $1.25 / 5 calls
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics()
        metrics.ai_api_calls = 3
        metrics.ai_api_cost = 0.75
        metrics.cache_hits = 10
        metrics.cache_misses = 2
        
        data = metrics.to_dict()
        
        assert data["ai_api_calls"] == 3
        assert data["ai_api_cost"] == 0.75
        assert data["cache_hit_ratio"] == 10/12  # 10 hits, 12 total
        assert data["cost_per_fix_attempt"] == 0.25


class TestPerformanceOptimizer:
    """Test the main performance optimization system."""
    
    def create_mock_session(self) -> AgentSession:
        """Create a mock agent session for testing."""
        config = AgentConfig()
        config.max_cost_per_session = 0.50
        config.max_session_duration = 600
        
        return AgentSession(
            session_id="test_session",
            repository=Mock(),
            current_state=Mock(),
            config=config,
            total_cost=0.25,
            start_time=time.time() - 300  # 5 minutes ago
        )
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = PerformanceOptimizer(OptimizationLevel.BALANCED)
        
        assert optimizer.optimization_level == OptimizationLevel.BALANCED
        assert isinstance(optimizer.cache, IntelligentCache)
        assert isinstance(optimizer.cost_optimizer, CostOptimizer)
        assert isinstance(optimizer.metrics, PerformanceMetrics)
    
    def test_session_timing(self):
        """Test session timing functionality."""
        optimizer = PerformanceOptimizer()
        
        session_id = "test_session_123"
        
        # Start timing
        optimizer.start_session_timing(session_id)
        
        # Simulate some work
        time.sleep(0.1)
        
        # End timing
        duration = optimizer.end_session_timing(session_id)
        
        assert duration >= 0.1
        assert optimizer.metrics.total_execution_time >= 0.1
        assert session_id not in optimizer._session_start_times
    
    def test_cache_usage_decisions(self):
        """Test cache usage decision logic."""
        # Aggressive mode
        aggressive_optimizer = PerformanceOptimizer(OptimizationLevel.AGGRESSIVE)
        assert aggressive_optimizer.should_use_cache(CacheType.CODE_SEARCH, "query", 0.001)
        
        # Conservative mode
        conservative_optimizer = PerformanceOptimizer(OptimizationLevel.CONSERVATIVE)
        assert not conservative_optimizer.should_use_cache(CacheType.CODE_SEARCH, "query", 0.001)
        assert conservative_optimizer.should_use_cache(CacheType.AI_RESPONSE, "prompt", 0.05)
        
        # Balanced mode
        balanced_optimizer = PerformanceOptimizer(OptimizationLevel.BALANCED)
        # Should use cost-based decision making
    
    def test_cache_operations_with_metrics(self):
        """Test cache operations update metrics correctly."""
        optimizer = PerformanceOptimizer()
        
        # Cache miss
        result = optimizer.get_from_cache(CacheType.REPOSITORY_ANALYSIS, "repo_path")
        assert result is None
        assert optimizer.metrics.cache_misses == 1
        assert optimizer.metrics.cache_hits == 0
        
        # Set cache
        optimizer.set_cache(CacheType.REPOSITORY_ANALYSIS, "repo_path", {"data": "test"})
        
        # Cache hit
        result = optimizer.get_from_cache(CacheType.REPOSITORY_ANALYSIS, "repo_path")
        assert result == {"data": "test"}
        assert optimizer.metrics.cache_hits == 1
        assert optimizer.metrics.cache_misses == 1
    
    def test_ai_call_recording(self):
        """Test AI call metrics recording."""
        optimizer = PerformanceOptimizer()
        
        # Record AI call
        optimizer.record_ai_call("gpt-4o-mini", input_tokens=500, output_tokens=200, cost=0.123)
        
        assert optimizer.metrics.ai_api_calls == 1
        assert optimizer.metrics.ai_api_cost == 0.123
        assert optimizer.metrics.tokens_used == 700
    
    def test_optimization_recommendations(self):
        """Test optimization strategy recommendations."""
        optimizer = PerformanceOptimizer()
        session = self.create_mock_session()
        
        # Set up some metrics
        optimizer.metrics.cache_hits = 2
        optimizer.metrics.cache_misses = 10  # Poor cache hit ratio
        optimizer.metrics.ai_api_calls = 5
        optimizer.metrics.ai_api_cost = 0.80  # High cost per attempt
        
        recommendations = optimizer.recommend_optimization_strategy(session)
        
        assert len(recommendations["recommendations"]) > 0
        
        # Should warn about cache efficiency
        cache_warnings = [r for r in recommendations["recommendations"] if r["type"] == "cache_efficiency"]
        assert len(cache_warnings) > 0
        
        # Should warn about high costs
        cost_warnings = [r for r in recommendations["recommendations"] if r["type"] == "model_optimization"]
        assert len(cost_warnings) > 0
    
    def test_optimization_settings(self):
        """Test getting optimized settings for tasks."""
        optimizer = PerformanceOptimizer(OptimizationLevel.AGGRESSIVE)
        session = self.create_mock_session()
        
        settings = optimizer.get_optimization_settings("simple", session)
        
        assert "model" in settings
        assert "max_tokens" in settings
        assert "temperature" in settings
        assert "use_cache" in settings
        
        # Aggressive mode should have lower token limit and temperature
        assert settings["max_tokens"] <= 800
        assert settings["temperature"] == 0.0
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        optimizer = PerformanceOptimizer()
        
        # Add some entries that will expire quickly
        optimizer.cache.set(CacheType.TEST_OUTPUT, "test1", "result1", ttl=0.1)
        optimizer.cache.set(CacheType.TEST_OUTPUT, "test2", "result2", ttl=0.1)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Cleanup
        cleanup_result = optimizer.cleanup_cache()
        
        assert cleanup_result["expired_entries_removed"] == 2
        assert cleanup_result["current_cache_size"] == 0
    
    def test_performance_summary(self):
        """Test getting comprehensive performance summary."""
        optimizer = PerformanceOptimizer()
        
        # Add some activity
        optimizer.record_ai_call("gpt-4o-mini", 100, 50, 0.02)
        optimizer.set_cache(CacheType.AI_RESPONSE, "prompt", "response")
        optimizer.get_from_cache(CacheType.AI_RESPONSE, "prompt")
        
        summary = optimizer.get_performance_summary()
        
        assert "metrics" in summary
        assert "cache_stats" in summary
        assert "optimization_level" in summary
        assert "active_sessions" in summary
        
        assert summary["optimization_level"] == OptimizationLevel.BALANCED.value
        assert summary["metrics"]["ai_api_calls"] == 1
        assert summary["metrics"]["cache_hits"] == 1


class TestOptimizationLevels:
    """Test different optimization levels."""
    
    def test_conservative_optimization(self):
        """Test conservative optimization behavior."""
        optimizer = PerformanceOptimizer(OptimizationLevel.CONSERVATIVE)
        
        # Should be more cautious about caching
        assert not optimizer.should_use_cache(CacheType.CODE_SEARCH, "query", 0.01)
        assert optimizer.should_use_cache(CacheType.AI_RESPONSE, "prompt", 0.05)
        
        # Settings should favor accuracy over speed
        session = Mock()
        session.total_cost = 0.10
        session.config.max_cost_per_session = 0.50
        
        settings = optimizer.get_optimization_settings("medium", session)
        assert settings["max_tokens"] == 1500  # Higher token limit
        assert settings["temperature"] == 0.2   # More creative
        assert settings["cache_ttl"] == 1800    # Shorter cache
    
    def test_aggressive_optimization(self):
        """Test aggressive optimization behavior."""
        optimizer = PerformanceOptimizer(OptimizationLevel.AGGRESSIVE)
        
        # Should cache everything
        assert optimizer.should_use_cache(CacheType.CODE_SEARCH, "query", 0.001)
        
        # Settings should favor speed over accuracy
        session = Mock()
        session.total_cost = 0.10
        session.config.max_cost_per_session = 0.50
        
        settings = optimizer.get_optimization_settings("medium", session)
        assert settings["max_tokens"] == 800    # Lower token limit
        assert settings["temperature"] == 0.0   # More deterministic
        assert settings["cache_ttl"] == 7200    # Longer cache
    
    def test_balanced_optimization(self):
        """Test balanced optimization behavior."""
        optimizer = PerformanceOptimizer(OptimizationLevel.BALANCED)
        
        # Should use cost-based decisions
        # This is tested indirectly through the cost optimizer integration


class TestIntegration:
    """Integration tests for performance optimization."""
    
    def test_end_to_end_optimization_workflow(self):
        """Test complete optimization workflow."""
        optimizer = PerformanceOptimizer(OptimizationLevel.BALANCED)
        
        # Simulate a session
        session_id = "integration_test"
        optimizer.start_session_timing(session_id)
        
        # Simulate repository analysis (expensive operation)
        repo_data = {"language": "python", "framework": "pytest"}
        if optimizer.should_use_cache(CacheType.REPOSITORY_ANALYSIS, "test_repo", 0.05):
            optimizer.set_cache(CacheType.REPOSITORY_ANALYSIS, "test_repo", repo_data)
        
        # Simulate AI API calls
        optimizer.record_ai_call("gpt-4o-mini", 800, 200, 0.15)
        optimizer.record_ai_call("gpt-4o-mini", 600, 150, 0.12)
        
        # Get from cache
        cached_data = optimizer.get_from_cache(CacheType.REPOSITORY_ANALYSIS, "test_repo")
        assert cached_data == repo_data
        
        # End session
        duration = optimizer.end_session_timing(session_id)
        
        # Get performance summary
        summary = optimizer.get_performance_summary()
        
        # Verify metrics
        assert summary["metrics"]["ai_api_calls"] == 2
        assert summary["metrics"]["ai_api_cost"] == 0.27
        assert summary["metrics"]["cache_hits"] == 1
        assert summary["metrics"]["total_execution_time"] >= duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])