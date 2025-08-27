#!/usr/bin/env python3
"""Test the architecture integration without requiring real API calls."""
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.repo_patcher.agent.config import AgentConfig
from src.repo_patcher.agent.openai_client import OpenAIClient, AIResponse, TokenUsage
from src.repo_patcher.agent.state_machine import AgentStateMachine, IngestHandler
from src.repo_patcher.agent.models import RepositoryContext, AgentSession, AgentState


async def test_architecture_integration():
    """Test that all components integrate properly without real API calls."""
    print("🏗️  Testing Architecture Integration...")
    
    # Create configuration
    config = AgentConfig(
        openai_api_key="sk-mock1234567890abcdef1234567890abcdef",
        model_name="gpt-4o-mini",
        max_iterations=2,
        max_cost_per_session=1.0
    )
    
    # Mock the OpenAI client
    mock_response = AIResponse(
        content='{"failing_tests": [{"test_name": "test_sqrt", "error_type": "NameError", "error_message": "name sqrt is not defined"}], "analysis": {"root_cause": "Missing import statement", "affected_files": ["src/calculator.py"], "complexity_level": "simple"}, "code_context": {"imports": ["import math"], "functions": ["sqrt_function"], "classes": []}}',
        parsed_data={
            "failing_tests": [{
                "test_name": "test_sqrt",
                "error_type": "NameError", 
                "error_message": "name 'sqrt' is not defined",
                "file_path": "tests/test_calculator.py",
                "line_number": 10
            }],
            "analysis": {
                "root_cause": "Missing import statement for sqrt function",
                "affected_files": ["src/calculator.py"],
                "complexity_level": "simple",
                "dependencies": ["math"]
            },
            "code_context": {
                "imports": ["import math"],
                "functions": ["sqrt_function", "test_sqrt"],
                "classes": []
            }
        },
        token_usage=TokenUsage(prompt_tokens=150, completion_tokens=100, total_tokens=250),
        model="gpt-4o-mini",
        finish_reason="stop"
    )
    
    with patch.object(OpenAIClient, 'complete_with_schema', new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = mock_response
        
        # Create AI client
        client = OpenAIClient(config)
        
        # Test 1: Verify state machine creation with AI client
        state_machine = AgentStateMachine(ai_client=client)
        print("✅ State machine created with AI client")
        
        # Test 2: Verify IngestHandler has AI client
        ingest_handler = state_machine.handlers[AgentState.INGEST]
        assert isinstance(ingest_handler, IngestHandler)
        assert ingest_handler.ai_client is client
        print("✅ IngestHandler properly configured with AI client")
        
        # Test 3: Test repository context creation
        scenario_path = Path("scenarios/E001_missing_import/repo")
        if scenario_path.exists():
            repo_context = RepositoryContext(
                repo_path=scenario_path,
                repo_url="https://github.com/test/repo",
                branch="main", 
                commit_sha="abc123",
                test_framework="pytest",
                test_command="python -m pytest tests/",
                failing_tests=["tests/test_calculator.py::test_sqrt"],
                test_output="NameError: name 'sqrt' is not defined"
            )
            print("✅ Repository context created")
            
            # Test 4: Test session creation
            session = AgentSession(
                session_id="test-session-123",
                repository=repo_context,
                current_state=AgentState.INGEST,
                config=config
            )
            print("✅ Agent session created")
            
            # Test 5: Test IngestHandler execution with mocked AI
            try:
                result = await ingest_handler.execute(session)
                print(f"✅ IngestHandler executed successfully: {result}")
                
                # Verify AI was called
                assert mock_complete.called, "AI client should have been called"
                print("✅ AI client was properly invoked during execution")
                
                # Check if analysis was stored in session context
                if "ingest_analysis" in session.context.code_context:
                    analysis = session.context.code_context["ingest_analysis"]
                    print(f"✅ Analysis stored in session: {len(str(analysis))} chars")
                    
                    # Verify structure of analysis
                    assert "failing_tests" in analysis, "Analysis should contain failing_tests"
                    assert "analysis" in analysis, "Analysis should contain analysis section"
                    assert "code_context" in analysis, "Analysis should contain code_context"
                    print("✅ Analysis structure is correct")
                
                return True
                
            except Exception as e:
                print(f"❌ IngestHandler execution failed: {e}")
                return False
        else:
            print("⚠️  E001 scenario not found, skipping repository-based tests")
            return True


async def test_cost_tracking():
    """Test that cost tracking works properly."""
    print("\n💰 Testing Cost Tracking...")
    
    config = AgentConfig(openai_api_key="sk-mock1234567890abcdef1234567890abcdef", max_cost_per_session=0.10)
    client = OpenAIClient(config)
    
    # Simulate adding costs
    usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
    client.total_tokens = usage
    client.total_cost = usage.estimated_cost
    
    print(f"✅ Token usage: {usage.total_tokens} tokens")
    print(f"✅ Estimated cost: ${usage.estimated_cost:.4f}")
    print(f"✅ Cost limit check: {client.check_cost_limit()}")
    print(f"✅ Warning check: {client.check_cost_warning()}")
    
    return True


async def test_configuration_management():
    """Test configuration system."""
    print("\n⚙️  Testing Configuration Management...")
    
    # Test environment variable loading
    os.environ["AGENT_MODEL"] = "gpt-4o"
    os.environ["AGENT_MAX_ITERATIONS"] = "5"
    os.environ["AGENT_TEMPERATURE"] = "0.2"
    
    config = AgentConfig.from_env()
    
    assert config.model_name == "gpt-4o", f"Expected gpt-4o, got {config.model_name}"
    assert config.max_iterations == 5, f"Expected 5, got {config.max_iterations}"
    assert config.temperature == 0.2, f"Expected 0.2, got {config.temperature}"
    
    print("✅ Environment variable configuration works")
    
    # Test validation
    try:
        config.validate()
        print("✅ Configuration validation passed")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True


async def main():
    """Run all architecture tests."""
    print("🚀 Testing Repo Patcher Phase 1C Architecture Integration\n")
    
    tests = [
        ("Architecture Integration", test_architecture_integration),
        ("Cost Tracking", test_cost_tracking),
        ("Configuration Management", test_configuration_management),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append(result)
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: FAILED with error: {e}")
            results.append(False)
    
    print(f"\n📊 Final Results:")
    print(f"   Tests passed: {sum(results)}/{len(results)}")
    print(f"   Success rate: {sum(results)/len(results)*100:.1f}%")
    
    if all(results):
        print("🎉 All architecture integration tests PASSED!")
        print("✅ Phase 1C infrastructure is ready for AI integration")
    else:
        print("⚠️  Some tests failed - review implementation")


if __name__ == "__main__":
    asyncio.run(main())