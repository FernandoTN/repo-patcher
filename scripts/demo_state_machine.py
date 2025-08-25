#!/usr/bin/env python3
"""Demo script showing the state machine in action."""
import asyncio
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_patcher.agent.runner import AgentEvaluationRunner


async def demo_agent():
    """Demonstrate the agent state machine."""
    print("🤖 Repo Patcher Agent Demo")
    print("=" * 50)
    
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    
    if not scenarios_dir.exists():
        print("❌ No scenarios directory found!")
        return
    
    runner = AgentEvaluationRunner(scenarios_dir)
    scenarios = runner.list_scenarios()
    
    if not scenarios:
        print("❌ No scenarios found!")
        return
    
    print(f"📋 Found {len(scenarios)} scenarios:")
    for scenario in scenarios:
        print(f"   - {scenario}")
    
    print(f"\n🚀 Running scenario: {scenarios[0]}")
    print("=" * 50)
    
    result = await runner.run_scenario(scenarios[0])
    
    print(f"✅ Result: {result.result.value}")
    print(f"⏱️  Duration: {result.total_duration:.3f}s")
    print(f"💰 Cost: ${result.total_cost:.4f}")
    print(f"🔄 Attempts: {len(result.attempts)}")
    print(f"📏 Diff Size: {result.final_diff_size} lines")
    
    if result.error_message:
        print(f"⚠️  Error: {result.error_message}")
    
    print("\n📊 State Machine Execution:")
    print("-" * 30)
    
    # The actual execution details would be in the session
    # For now, just show the mock results
    print("1. INGEST → Analyzed repository structure")
    print("2. PLAN   → Created fix strategy")  
    print("3. PATCH  → Applied code changes")
    print("4. TEST   → Validated fixes")
    print("5. DONE   → Created successful fix")
    
    print("\n🎉 Demo completed!")


def main():
    """Run the demo."""
    asyncio.run(demo_agent())


if __name__ == "__main__":
    main()