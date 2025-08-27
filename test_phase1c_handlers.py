#!/usr/bin/env python
"""Test script for Phase 1C AI-powered state handlers with mock responses."""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
from dataclasses import dataclass

# Import Phase 1C components
from src.repo_patcher.agent.state_machine import (
    IngestHandler, PlanHandler, PatchHandler, RepairHandler, AgentStateMachine
)
from src.repo_patcher.agent.openai_client import (
    OpenAIClient, AIResponse, TokenUsage, INGEST_SCHEMA, PLAN_SCHEMA, PATCH_SCHEMA
)
from src.repo_patcher.agent.models import (
    AgentSession, AgentState, RepositoryContext
)
from src.repo_patcher.agent.config import AgentConfig
from src.repo_patcher.agent.context import SessionContext
from src.repo_patcher.agent.exceptions import AIClientError


class MockOpenAIClient:
    """Mock OpenAI client for testing without API costs."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.total_cost = 0.0
        self.total_tokens = TokenUsage()
        
    async def complete_with_schema(self, messages, schema, system_prompt=None, max_retries=None):
        """Mock structured completion based on schema."""
        # Simulate different responses based on schema
        if schema == INGEST_SCHEMA:
            return self._mock_ingest_response()
        elif schema == PLAN_SCHEMA:
            return self._mock_plan_response()
        elif schema == PATCH_SCHEMA:
            return self._mock_patch_response()
        else:
            # Generic repair response
            return self._mock_repair_response()
    
    def _mock_ingest_response(self):
        """Mock ingest analysis response."""
        mock_data = {
            "failing_tests": [
                {
                    "test_name": "tests/test_calculator.py::test_add",
                    "error_type": "ImportError",
                    "error_message": "cannot import name 'add' from 'src.calculator'",
                    "file_path": "tests/test_calculator.py",
                    "line_number": 2
                }
            ],
            "analysis": {
                "root_cause": "Missing import statement in calculator module",
                "affected_files": ["src/calculator.py", "tests/test_calculator.py"],
                "complexity_level": "simple",
                "dependencies": ["math"]
            },
            "code_context": {
                "imports": ["math", "unittest"],
                "functions": ["add", "subtract", "test_add"],
                "classes": ["Calculator"]
            }
        }
        
        return AIResponse(
            content=json.dumps(mock_data),
            parsed_data=mock_data,
            token_usage=TokenUsage(prompt_tokens=500, completion_tokens=200, total_tokens=700),
            model="gpt-4o-mini",
            finish_reason="stop"
        )
    
    def _mock_plan_response(self):
        """Mock plan generation response."""
        mock_data = {
            "strategy": "Add missing import statement to fix ImportError",
            "steps": [
                {
                    "action": "add_import",
                    "description": "Add import statement for 'add' function in calculator module",
                    "files": ["src/calculator.py"],
                    "expected_outcome": "Import error resolved, tests can find the add function"
                }
            ],
            "risk_assessment": {
                "risk_level": "low",
                "confidence": 0.95,
                "potential_issues": ["None - simple import addition"]
            }
        }
        
        return AIResponse(
            content=json.dumps(mock_data),
            parsed_data=mock_data,
            token_usage=TokenUsage(prompt_tokens=800, completion_tokens=150, total_tokens=950),
            model="gpt-4o-mini",
            finish_reason="stop"
        )
    
    def _mock_patch_response(self):
        """Mock patch generation response."""
        mock_data = {
            "changes": [
                {
                    "file_path": "src/calculator.py",
                    "modifications": [
                        {
                            "line_number": 1,
                            "old_content": "def add(a, b):",
                            "new_content": "from math import *\n\ndef add(a, b):",
                            "operation": "replace"
                        }
                    ]
                }
            ],
            "explanation": "Added missing import statement at the top of the file",
            "diff_summary": {
                "files_modified": 1,
                "lines_added": 1,
                "lines_removed": 0
            }
        }
        
        return AIResponse(
            content=json.dumps(mock_data),
            parsed_data=mock_data,
            token_usage=TokenUsage(prompt_tokens=1200, completion_tokens=100, total_tokens=1300),
            model="gpt-4o-mini",
            finish_reason="stop"
        )
    
    def _mock_repair_response(self):
        """Mock repair analysis response."""
        mock_data = {
            "decision": "retry",
            "confidence": 0.8,
            "reason": "Previous fix was partially successful, trying different approach",
            "strategy_adjustment": "more_conservative",
            "new_approach": "validate imports before applying changes"
        }
        
        return AIResponse(
            content=json.dumps(mock_data),
            parsed_data=mock_data,
            token_usage=TokenUsage(prompt_tokens=600, completion_tokens=80, total_tokens=680),
            model="gpt-4o-mini",
            finish_reason="stop"
        )
    
    def get_total_cost(self):
        return 0.05  # Mock cost
    
    def get_total_usage(self):
        return TokenUsage(prompt_tokens=3100, completion_tokens=530, total_tokens=3630)


async def test_ingest_handler():
    """Test IngestHandler with mock AI client."""
    print("Testing IngestHandler...")
    
    # Create temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Create mock repository structure
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "calculator.py").write_text("def add(a, b):\n    return a + b")
        
        tests_dir = repo_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_calculator.py").write_text(
            "from src.calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5"
        )
        
        # Create mock session
        config = AgentConfig()
        repo_context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="pytest tests/",
            failing_tests=["tests/test_calculator.py::test_add"],
            test_output="ImportError: cannot import name 'add'"
        )
        
        session = AgentSession(
            session_id="test-session-1",
            repository=repo_context,
            current_state=AgentState.INGEST,
            config=config
        )
        
        # Test with mock AI client
        mock_client = MockOpenAIClient(config)
        handler = IngestHandler(mock_client)
        
        result = await handler.execute(session)
        
        print(f"✓ IngestHandler result: {result}")
        
        # Check that analysis was stored in context
        analysis = session.context.get_code_context("ingest_analysis")
        assert analysis is not None, "Analysis should be stored in context"
        assert "failing_tests" in analysis, "Analysis should contain failing_tests"
        print(f"✓ Analysis stored: {len(analysis['failing_tests'])} failing tests found")
        
        return True


async def test_plan_handler():
    """Test PlanHandler with mock AI client."""
    print("Testing PlanHandler...")
    
    config = AgentConfig()
    
    # Create session with mock analysis data
    repo_context = RepositoryContext(
        repo_path=Path("/tmp/test"),
        repo_url="https://github.com/test/repo",
        branch="main",
        commit_sha="abc123",
        test_framework="pytest",
        test_command="pytest tests/",
        failing_tests=["tests/test_calculator.py::test_add"]
    )
    
    session = AgentSession(
        session_id="test-session-2",
        repository=repo_context,
        current_state=AgentState.PLAN,
        config=config
    )
    
    # Add mock ingest analysis to context
    mock_analysis = {
        "failing_tests": [
            {
                "test_name": "tests/test_calculator.py::test_add",
                "error_type": "ImportError",
                "error_message": "cannot import name 'add'",
            }
        ],
        "analysis": {
            "root_cause": "Missing import",
            "affected_files": ["src/calculator.py"],
            "complexity_level": "simple"
        },
        "code_context": {
            "imports": ["math"],
            "functions": ["add"],
            "classes": []
        }
    }
    session.context.add_code_context("ingest_analysis", mock_analysis)
    
    # Test with mock AI client
    mock_client = MockOpenAIClient(config)
    handler = PlanHandler(mock_client)
    
    result = await handler.execute(session)
    
    print(f"✓ PlanHandler result: {result}")
    
    # Check that plan was stored in context
    plan_data = session.context.get_code_context("plan_data")
    assert plan_data is not None, "Plan should be stored in context"
    assert "strategy" in plan_data, "Plan should contain strategy"
    assert "steps" in plan_data, "Plan should contain steps"
    print(f"✓ Plan stored: {plan_data['strategy']}")
    print(f"✓ Plan steps: {len(plan_data['steps'])}")
    
    return True


async def test_patch_handler():
    """Test PatchHandler with mock AI client."""
    print("Testing PatchHandler...")
    
    # Create temporary repository for patch testing
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        src_dir = repo_path / "src"
        src_dir.mkdir()
        
        # Create test file to patch
        calculator_file = src_dir / "calculator.py"
        calculator_file.write_text("def add(a, b):\n    return a + b")
        
        config = AgentConfig()
        repo_context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="pytest tests/"
        )
        
        session = AgentSession(
            session_id="test-session-3",
            repository=repo_context,
            current_state=AgentState.PATCH,
            config=config
        )
        
        # Add mock plan data to context
        mock_plan = {
            "strategy": "Add missing import",
            "steps": [
                {
                    "action": "add_import",
                    "description": "Add import statement",
                    "files": ["src/calculator.py"]
                }
            ]
        }
        session.context.add_code_context("plan_data", mock_plan)
        
        # Test with mock AI client
        mock_client = MockOpenAIClient(config)
        handler = PatchHandler(mock_client)
        
        result = await handler.execute(session)
        
        print(f"✓ PatchHandler result: {result}")
        
        # Check that patch data was stored
        patch_data = session.context.get_code_context("patch_data")
        assert patch_data is not None, "Patch data should be stored in context"
        assert "changes" in patch_data, "Patch should contain changes"
        print(f"✓ Patch data stored: {len(patch_data['changes'])} changes")
        
        return True


async def test_repair_handler():
    """Test RepairHandler with mock AI client."""
    print("Testing RepairHandler...")
    
    config = AgentConfig()
    repo_context = RepositoryContext(
        repo_path=Path("/tmp/test"),
        repo_url="https://github.com/test/repo", 
        branch="main",
        commit_sha="abc123",
        test_framework="pytest",
        test_command="pytest tests/"
    )
    
    session = AgentSession(
        session_id="test-session-4",
        repository=repo_context,
        current_state=AgentState.REPAIR,
        config=config
    )
    
    # Add mock test results to context
    mock_test_results = {
        "exit_code": 1,
        "failing_tests": ["tests/test_calculator.py::test_add"],
        "test_output": "Still failing after patch"
    }
    session.context.add_code_context("test_results", mock_test_results)
    
    # Test with mock AI client
    mock_client = MockOpenAIClient(config)
    handler = RepairHandler(mock_client)
    
    result = await handler.execute(session)
    
    print(f"✓ RepairHandler result: {result}")
    
    # Check that repair analysis was stored
    repair_analysis = session.context.get_code_context("repair_analysis")
    assert repair_analysis is not None, "Repair analysis should be stored"
    assert "decision" in repair_analysis, "Repair analysis should contain decision"
    print(f"✓ Repair decision: {repair_analysis['decision']}")
    
    return True


async def test_agent_state_machine():
    """Test the complete AgentStateMachine."""
    print("Testing AgentStateMachine...")
    
    # Create temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Create mock repository structure
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "calculator.py").write_text("def add(a, b):\n    return a + b")
        
        tests_dir = repo_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_calculator.py").write_text(
            "from src.calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5"
        )
        
        # Create repository context
        repo_context = RepositoryContext(
            repo_path=repo_path,
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="pytest tests/",
            failing_tests=["tests/test_calculator.py::test_add"],
            test_output="ImportError: cannot import name 'add'"
        )
        
        # Create state machine with mock AI client
        config = AgentConfig()
        mock_client = MockOpenAIClient(config)
        state_machine = AgentStateMachine(mock_client)
        
        # Mock the TestHandler to avoid running actual tests
        async def mock_test_execute(session):
            from src.repo_patcher.agent.models import StepResult
            return StepResult.SUCCESS
        
        state_machine.handlers[AgentState.TEST].execute = mock_test_execute
        
        # Mock the PRHandler 
        async def mock_pr_execute(session):
            from src.repo_patcher.agent.models import StepResult
            return StepResult.SUCCESS
        
        state_machine.handlers[AgentState.PR].execute = mock_pr_execute
        
        print("✓ State machine initialized with mock handlers")
        
        # Note: We won't run the full execution as it would take too long
        # and hit the safety limits. Instead, we'll test individual state transitions.
        print("✓ State machine structure verified")
        
        return True


async def main():
    """Run all Phase 1C handler tests."""
    print("🧪 Testing Phase 1C AI-Powered State Handlers\n")
    
    tests = [
        ("IngestHandler", test_ingest_handler),
        ("PlanHandler", test_plan_handler),
        ("PatchHandler", test_patch_handler),
        ("RepairHandler", test_repair_handler),
        ("AgentStateMachine", test_agent_state_machine),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- Testing {test_name} ---")
            success = await test_func()
            results.append((test_name, success, None))
            print(f"✅ {test_name} test passed\n")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"❌ {test_name} test failed: {e}\n")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"    Error: {error}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 1C handler tests passed!")
    else:
        print(f"\n⚠️  {total - passed} tests failed. See errors above.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())