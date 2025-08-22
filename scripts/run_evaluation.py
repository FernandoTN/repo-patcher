#!/usr/bin/env python3
"""Script to run evaluation scenarios."""
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_patcher.evaluation.runner import EvaluationRunner


def main():
    """Run evaluation scenarios."""
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    runner = EvaluationRunner(scenarios_dir)
    
    print("Available scenarios:")
    scenarios = runner.list_scenarios()
    for scenario in scenarios:
        print(f"  - {scenario}")
    
    print(f"\nTesting scenario: {scenarios[0]}")
    result = runner.run_scenario(scenarios[0])
    
    print(f"Result: {result.result.value}")
    print(f"Error: {result.error_message}")
    
    # Test the evaluation report
    print("\nRunning all scenarios...")
    report = runner.run_all_scenarios()
    report_text = runner.generate_report(report)
    print(report_text)


if __name__ == "__main__":
    main()