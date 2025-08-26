#!/usr/bin/env python3
"""Test script to verify AI integration works properly."""
import asyncio
import os
from pathlib import Path
import tempfile

# API key should be set via environment variable for security

from src.repo_patcher.agent.config import AgentConfig
from src.repo_patcher.agent.openai_client import OpenAIClient
from src.repo_patcher.agent.state_machine import AgentStateMachine
from src.repo_patcher.agent.models import RepositoryContext, AgentSession, AgentState


async def test_ai_client():
    """Test basic AI client functionality."""
    print("🔧 Testing OpenAI client...")
    
    config = AgentConfig.from_env()
    client = OpenAIClient(config)
    
    # Test simple completion
    response = await client.simple_complete(
        messages=[{"role": "user", "content": "Say 'AI integration test successful'"}]
    )
    
    print(f"✅ AI Response: {response.content}")
    print(f"💰 Cost: ${response.token_usage.estimated_cost:.4f}")
    print(f"🔢 Tokens: {response.token_usage.total_tokens}")
    
    return client


async def test_ingest_handler():
    """Test IngestHandler with real AI integration."""
    print("\n🏗️  Testing IngestHandler with AI...")
    
    config = AgentConfig.from_env()
    client = OpenAIClient(config)
    state_machine = AgentStateMachine(ai_client=client)
    
    # Use the existing E001 scenario
    scenario_path = Path("scenarios/E001_missing_import/repo")
    
    if not scenario_path.exists():
        print("❌ E001 scenario not found. Creating a simple test case...")
        return
    
    # Create repository context
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
    
    # Execute just the INGEST state
    ingest_handler = state_machine.handlers[AgentState.INGEST]
    session = AgentSession(
        session_id="test-session",
        repository=repo_context,
        current_state=AgentState.INGEST,
        config=config
    )
    
    try:
        result = await ingest_handler.execute(session)
        print(f"✅ Ingest completed with result: {result}")
        print(f"💰 Total cost: ${client.get_total_cost():.4f}")
        
        # Check if AI analysis was stored
        if "ingest_analysis" in session.context.code_context:
            analysis = session.context.code_context["ingest_analysis"]
            print(f"🧠 AI Analysis available: {len(str(analysis))} chars")
            print(f"📊 Failing tests identified: {len(analysis.get('failing_tests', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting AI Integration Tests for Repo Patcher Phase 1C\n")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY=your-actual-key")
        return
    
    try:
        # Test 1: Basic AI Client
        client = await test_ai_client()
        
        # Test 2: IngestHandler with AI
        success = await test_ingest_handler()
        
        print(f"\n📊 Final Results:")
        print(f"   Total Cost: ${client.get_total_cost():.4f}")
        print(f"   Status: {'✅ All tests passed' if success else '❌ Some tests failed'}")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(main())