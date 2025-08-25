"""Command-line interface for Repo Patcher."""
import asyncio
import click
import json
from pathlib import Path
from typing import Optional

from .agent.config import AgentConfig
from .agent.logging_config import setup_logging
from .agent.runner import AgentEvaluationRunner
from .evaluation.runner import EvaluationRunner


@click.group()
@click.option('--config', type=click.Path(exists=True), help='Configuration file path')
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.option('--log-file', type=click.Path(), help='Log file path')
@click.option('--structured-logs', is_flag=True, help='Use structured JSON logging')
@click.pass_context
def cli(ctx, config, log_level, log_file, structured_logs):
    """Repo Patcher - AI-powered test fixing agent."""
    ctx.ensure_object(dict)
    
    # Set up logging
    setup_logging(
        level=log_level,
        log_file=Path(log_file) if log_file else None,
        structured=structured_logs
    )
    
    # Load configuration
    if config:
        ctx.obj['config'] = AgentConfig.from_file(Path(config))
    else:
        ctx.obj['config'] = AgentConfig.from_env()


@cli.command()
@click.argument('scenarios_dir', type=click.Path(exists=True))
@click.option('--scenario', help='Run specific scenario only')
@click.option('--use-agent', is_flag=True, help='Use AI agent to fix scenarios')
@click.pass_context
def evaluate(ctx, scenarios_dir, scenario, use_agent):
    """Run evaluation scenarios."""
    scenarios_path = Path(scenarios_dir)
    
    if use_agent:
        runner = AgentEvaluationRunner(scenarios_path)
        click.echo("🤖 Running evaluation with AI agent...")
    else:
        runner = EvaluationRunner(scenarios_path)
        click.echo("📋 Running evaluation without agent (testing framework only)...")
    
    async def run_evaluation():
        if scenario:
            click.echo(f"Running scenario: {scenario}")
            result = await runner.run_scenario(scenario) if use_agent else runner.run_scenario(scenario)
            
            click.echo(f"Result: {result.result.value}")
            click.echo(f"Duration: {result.total_duration:.3f}s")
            click.echo(f"Cost: ${result.total_cost:.4f}")
            
            if result.error_message:
                click.echo(f"Error: {result.error_message}")
        else:
            click.echo("Running all scenarios...")
            if use_agent:
                report = await runner.run_all_scenarios()
            else:
                report = runner.run_all_scenarios()
            
            report_text = runner.generate_report(report)
            click.echo(report_text)
    
    if use_agent:
        asyncio.run(run_evaluation())
    else:
        asyncio.run(run_evaluation())


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output configuration file')
def config(output):
    """Generate configuration file."""
    config_obj = AgentConfig()
    config_data = {
        'max_iterations': config_obj.max_iterations,
        'max_session_duration': config_obj.max_session_duration,
        'max_cost_per_session': config_obj.max_cost_per_session,
        'model_name': config_obj.model_name,
        'temperature': config_obj.temperature,
        'test_timeout': config_obj.test_timeout,
        'blocked_paths': config_obj.blocked_paths,
        'allowed_file_types': config_obj.allowed_file_types,
    }
    
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        click.echo(f"Configuration written to {output_path}")
    else:
        click.echo(json.dumps(config_data, indent=2))


@cli.command()
@click.argument('scenarios_dir', type=click.Path(exists=True))
def demo(scenarios_dir):
    """Run interactive demo."""
    scenarios_path = Path(scenarios_dir)
    
    click.echo("🤖 Repo Patcher Interactive Demo")
    click.echo("=" * 50)
    
    runner = EvaluationRunner(scenarios_path)
    scenarios = runner.list_scenarios()
    
    if not scenarios:
        click.echo("❌ No scenarios found!")
        return
    
    click.echo(f"📋 Available scenarios ({len(scenarios)}):")
    for i, scenario in enumerate(scenarios, 1):
        click.echo(f"   {i}. {scenario}")
    
    if click.confirm("\n🚀 Run with AI agent?"):
        agent_runner = AgentEvaluationRunner(scenarios_path)
        
        async def run_demo():
            click.echo(f"\n🤖 Running scenario: {scenarios[0]}")
            result = await agent_runner.run_scenario(scenarios[0])
            
            click.echo(f"✅ Result: {result.result.value}")
            click.echo(f"⏱️  Duration: {result.total_duration:.3f}s")
            click.echo(f"💰 Cost: ${result.total_cost:.4f}")
            click.echo(f"🔄 Attempts: {len(result.attempts)}")
            
            if result.error_message:
                click.echo(f"⚠️  Error: {result.error_message}")
        
        asyncio.run(run_demo())
    else:
        click.echo(f"\n📋 Testing framework with scenario: {scenarios[0]}")
        result = runner.run_scenario(scenarios[0])
        
        click.echo(f"Result: {result.result.value}")
        click.echo(f"Error: {result.error_message}")
    
    click.echo("\n🎉 Demo completed!")


@cli.command()
@click.argument('scenarios_dir', type=click.Path())
@click.argument('scenario_id')
@click.option('--description', required=True, help='Scenario description')
@click.option('--category', default='logic_error', help='Scenario category')
@click.option('--difficulty', default='medium', help='Scenario difficulty')
def create_scenario(scenarios_dir, scenario_id, description, category, difficulty):
    """Create a new evaluation scenario."""
    scenarios_path = Path(scenarios_dir)
    scenario_path = scenarios_path / scenario_id
    
    if scenario_path.exists():
        click.echo(f"❌ Scenario {scenario_id} already exists!")
        return
    
    # Create directory structure
    (scenario_path / "repo" / "src").mkdir(parents=True, exist_ok=True)
    (scenario_path / "repo" / "tests").mkdir(parents=True, exist_ok=True)
    (scenario_path / "expected_fix" / "src").mkdir(parents=True, exist_ok=True)
    (scenario_path / "expected_fix" / "tests").mkdir(parents=True, exist_ok=True)
    
    # Create scenario metadata
    metadata = {
        "id": scenario_id.split('_')[0].upper(),
        "name": scenario_id.split('_', 1)[1] if '_' in scenario_id else scenario_id,
        "description": description,
        "category": category,
        "difficulty": difficulty,
        "expected_iterations": 1,
        "expected_diff_lines": 5,
        "test_framework": "pytest",
        "language": "python",
        "files_to_change": ["src/example.py"],
        "test_command": "python -m pytest tests/ -v",
        "expected_error_patterns": ["Error pattern here"],
        "learning_objectives": [
            f"Learn to fix {category} issues",
            "Understand error patterns"
        ]
    }
    
    with open(scenario_path / "scenario.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Create placeholder files
    (scenario_path / "repo" / "src" / "example.py").write_text('''"""Example module with issues."""


def example_function():
    """Example function that needs fixing."""
    # TODO: Add broken code here
    pass
''')
    
    (scenario_path / "repo" / "tests" / "test_example.py").write_text('''"""Tests for example module."""
import pytest
from src.example import example_function


def test_example_function():
    """Test that should fail initially."""
    result = example_function()
    assert result is not None  # This should fail
''')
    
    (scenario_path / "expected_fix" / "src" / "example.py").write_text('''"""Example module with fixes."""


def example_function():
    """Example function that works correctly."""
    # TODO: Add fixed code here
    return "fixed"
''')
    
    (scenario_path / "expected_fix" / "tests" / "test_example.py").write_text('''"""Tests for example module."""
import pytest
from src.example import example_function


def test_example_function():
    """Test that should pass after fixing."""
    result = example_function()
    assert result is not None  # This should pass
''')
    
    click.echo(f"✅ Created scenario {scenario_id} at {scenario_path}")
    click.echo("📝 Edit the generated files to implement your test scenario")


if __name__ == '__main__':
    cli()