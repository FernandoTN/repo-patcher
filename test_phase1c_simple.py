#!/usr/bin/env python
"""Simple test for Phase 1C components without long-running operations."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Import Phase 1C components
from src.repo_patcher.agent.state_machine import (
    IngestHandler, PlanHandler, PatchHandler, RepairHandler
)
from src.repo_patcher.agent.openai_client import (
    AIResponse, TokenUsage, INGEST_SCHEMA, PLAN_SCHEMA, PATCH_SCHEMA
)
from src.repo_patcher.agent.models import (
    AgentSession, AgentState, RepositoryContext
)
from src.repo_patcher.agent.config import AgentConfig
from src.repo_patcher.agent.context import SessionContext


class QuickMockAIClient:
    """Minimal mock AI client."""
    
    def __init__(self):
        self.total_cost = 0.01
        
    async def complete_with_schema(self, messages, schema, system_prompt=None, max_retries=None):
        """Return mock responses based on schema type."""
        if schema == INGEST_SCHEMA:
            return AIResponse(
                content='{"failing_tests": [], "analysis": {"root_cause": "test", "affected_files": [], "complexity_level": "simple"}, "code_context": {"imports": [], "functions": [], "classes": []}}',
                parsed_data={"failing_tests": [], "analysis": {"root_cause": "test", "affected_files": [], "complexity_level": "simple"}, "code_context": {"imports": [], "functions": [], "classes": []}},
                token_usage=TokenUsage(100, 50, 150)
            )
        elif schema == PLAN_SCHEMA:
            return AIResponse(
                content='{"strategy": "test strategy", "steps": [], "risk_assessment": {"risk_level": "low", "confidence": 0.9}}',
                parsed_data={"strategy": "test strategy", "steps": [], "risk_assessment": {"risk_level": "low", "confidence": 0.9}},
                token_usage=TokenUsage(100, 50, 150)
            )
        elif schema == PATCH_SCHEMA:
            return AIResponse(
                content='{"changes": [], "explanation": "test patch"}',
                parsed_data={"changes": [], "explanation": "test patch"},
                token_usage=TokenUsage(100, 50, 150)
            )
        else:
            return AIResponse(
                content='{"decision": "escalate", "confidence": 0.5, "reason": "test"}',
                parsed_data={"decision": "escalate", "confidence": 0.5, "reason": "test"},
                token_usage=TokenUsage(100, 50, 150)
            )


async def test_handlers():
    """Test all handlers with minimal setup."""
    print("🧪 Testing Phase 1C Handlers (Quick Test)")
    
    # Create minimal config and context
    config = AgentConfig()
    mock_client = QuickMockAIClient()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        (repo_path / "test.py").write_text("# test file")
        
        repo_context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="pytest tests/",
            failing_tests=["test.py::test_func"],
            test_output="test output"
        )
        
        session = AgentSession(
            session_id="test-session",
            repository=repo_context,
            current_state=AgentState.INGEST,
            config=config
        )
        
        # Test each handler
        handlers = [
            ("IngestHandler", IngestHandler(mock_client)),
            ("PlanHandler", PlanHandler(mock_client)),
            ("PatchHandler", PatchHandler(mock_client)),
            ("RepairHandler", RepairHandler(mock_client)),
        ]
        
        results = []
        
        for name, handler in handlers:
            try:
                print(f"Testing {name}...")
                
                # Set up session state appropriately
                if name == "PlanHandler":
                    session.context.add_code_context("ingest_analysis", {"test": "data"})
                elif name == "PatchHandler":  
                    session.context.add_code_context("plan_data", {"test": "plan"})
                elif name == "RepairHandler":
                    session.context.add_code_context("test_results", {"exit_code": 1, "failing_tests": []})
                
                # Mock the timeout context managers to avoid delays
                import src.repo_patcher.agent.shutdown as shutdown_module
                
                class MockManagedOperation:
                    def __init__(self, name):
                        pass
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                
                class MockOperationTimeout:
                    def __init__(self, timeout, name):
                        pass
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                
                # Temporarily replace the timeout functions
                original_managed_operation = shutdown_module.managed_operation
                original_operation_timeout = shutdown_module.operation_timeout
                
                shutdown_module.managed_operation = MockManagedOperation
                shutdown_module.operation_timeout = MockOperationTimeout
                
                try:
                    result = await handler.execute(session)
                    print(f"✅ {name}: {result}")
                    results.append((name, True, None))
                finally:
                    # Restore original functions
                    shutdown_module.managed_operation = original_managed_operation
                    shutdown_module.operation_timeout = original_operation_timeout
                    
            except Exception as e:
                print(f"❌ {name}: {e}")
                results.append((name, False, str(e)))
        
        # Print summary
        print("\n" + "="*40)
        print("HANDLER TEST RESULTS")
        print("="*40)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        for name, success, error in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {name}")
            if error:
                print(f"    Error: {error}")
        
        print(f"\nResults: {passed}/{total} handlers passed")
        
        return passed == total


async def test_ai_client_mock():
    """Test the mock AI client functionality."""
    print("\n🧪 Testing Mock AI Client")
    
    client = QuickMockAIClient()
    
    # Test different schema responses
    schemas = [
        ("Ingest", INGEST_SCHEMA),
        ("Plan", PLAN_SCHEMA),
        ("Patch", PATCH_SCHEMA),
    ]
    
    for name, schema in schemas:
        try:
            response = await client.complete_with_schema(
                messages=[{"role": "user", "content": "test"}],
                schema=schema
            )
            assert response.is_valid_json(), f"{name} response should be valid JSON"
            print(f"✅ {name} schema response: valid")
        except Exception as e:
            print(f"❌ {name} schema response: {e}")
    
    print("✅ Mock AI client tests completed")


async def main():
    """Run all tests."""
    print("🔧 Phase 1C Component Testing\n")
    
    try:
        # Test mock AI client
        await test_ai_client_mock()
        
        # Test handlers
        handlers_passed = await test_handlers()
        
        if handlers_passed:
            print("\n🎉 All Phase 1C handler tests passed!")
            return True
        else:
            print("\n⚠️  Some handler tests failed.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)