#!/usr/bin/env python3
"""
Phase 1D Infrastructure Verification Script

This script verifies that all Phase 1D infrastructure components are working correctly.
"""

import os
import sys
import yaml
import json
from pathlib import Path


def test_imports():
    """Test that all new modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from src.repo_patcher.monitoring.telemetry import get_telemetry_manager
        from src.repo_patcher.monitoring.health import get_health_monitor, get_health_report
        from src.repo_patcher.monitoring.metrics_server import MetricsServer
        print("  ✅ All monitoring modules import successfully")
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    
    return True


def test_health_monitoring():
    """Test health monitoring functionality."""
    print("🏥 Testing health monitoring...")
    
    try:
        from src.repo_patcher.monitoring.health import get_health_report
        
        report = get_health_report()
        print(f"  ✅ Health report generated: {report.status.value}")
        print(f"  ✅ {len(report.checks)} health checks configured")
        print(f"  ✅ Uptime: {report.uptime:.1f}s")
        
        # Check that we have expected health checks
        expected_checks = ['cpu_usage', 'memory_usage', 'disk_usage', 'openai_connectivity', 'git_availability', 'workspace_access']
        for check in expected_checks:
            if check in report.checks:
                print(f"    ✅ {check}: {report.checks[check]['status']}")
            else:
                print(f"    ❌ Missing health check: {check}")
                
    except Exception as e:
        print(f"  ❌ Health monitoring error: {e}")
        return False
    
    return True


def test_telemetry():
    """Test telemetry functionality.""" 
    print("📊 Testing telemetry...")
    
    try:
        # Disable OTEL for testing
        os.environ['OTEL_ENABLED'] = 'false'
        
        from src.repo_patcher.monitoring.telemetry import get_telemetry_manager, trace_span
        
        manager = get_telemetry_manager()
        print("  ✅ Telemetry manager created")
        
        # Test trace span
        with trace_span('test_operation', {'test': 'value'}):
            print("  ✅ Trace span context works")
        
        # Test metrics recording
        manager.record_fix_attempt(True, 1.5, 0.25, 10)
        print("  ✅ Metrics recording works")
        
    except Exception as e:
        print(f"  ❌ Telemetry error: {e}")
        return False
    
    return True


def test_metrics_server():
    """Test metrics server functionality."""
    print("🌐 Testing metrics server...")
    
    try:
        os.environ['METRICS_PORT'] = '0'  # Use port 0 for testing
        from src.repo_patcher.monitoring.metrics_server import MetricsServer
        
        server = MetricsServer('127.0.0.1', 0)
        print("  ✅ Metrics server can be instantiated")
        print(f"  ✅ Server configured for host: 127.0.0.1")
        
    except Exception as e:
        print(f"  ❌ Metrics server error: {e}")
        return False
    
    return True


def test_docker_config():
    """Test Docker configuration files."""
    print("🐳 Testing Docker configuration...")
    
    # Test Dockerfile exists and has expected content
    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print("  ❌ Dockerfile not found")
        return False
    
    dockerfile_content = dockerfile.read_text()
    if "FROM python:" in dockerfile_content and "ENTRYPOINT" in dockerfile_content:
        print("  ✅ Dockerfile has expected structure")
    else:
        print("  ❌ Dockerfile missing expected content")
        return False
    
    # Test docker-compose.yml
    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("  ❌ docker-compose.yml not found")
        return False
    
    try:
        with open(compose_file) as f:
            compose = yaml.safe_load(f)
        
        services = compose.get('services', {})
        expected_services = ['repo-patcher', 'repo-patcher-dev', 'jaeger', 'prometheus']
        
        for service in expected_services:
            if service in services:
                print(f"    ✅ Service '{service}' configured")
            else:
                print(f"    ❌ Service '{service}' missing")
        
    except Exception as e:
        print(f"  ❌ Docker compose error: {e}")
        return False
    
    return True


def test_github_actions():
    """Test GitHub Actions workflow files."""
    print("⚡ Testing GitHub Actions workflows...")
    
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("  ❌ .github/workflows directory not found")
        return False
    
    expected_workflows = ['fix-tests.yml', 'ci.yml', 'maintenance.yml']
    
    for workflow in expected_workflows:
        workflow_file = workflows_dir / workflow
        if not workflow_file.exists():
            print(f"  ❌ Workflow {workflow} not found")
            continue
        
        try:
            with open(workflow_file) as f:
                workflow_data = yaml.safe_load(f)
            
            if 'jobs' in workflow_data:
                print(f"    ✅ {workflow}: Valid syntax, {len(workflow_data['jobs'])} jobs")
            else:
                print(f"    ❌ {workflow}: Invalid structure")
                
        except Exception as e:
            print(f"    ❌ {workflow}: YAML error - {e}")
            return False
    
    return True


def test_monitoring_config():
    """Test monitoring configuration files."""
    print("📈 Testing monitoring configuration...")
    
    monitoring_dir = Path("monitoring")
    if not monitoring_dir.exists():
        print("  ❌ monitoring/ directory not found")
        return False
    
    # Test Prometheus config
    prometheus_config = monitoring_dir / "prometheus.yml"
    if prometheus_config.exists():
        try:
            with open(prometheus_config) as f:
                prometheus = yaml.safe_load(f)
            print("  ✅ Prometheus configuration valid")
        except Exception as e:
            print(f"  ❌ Prometheus config error: {e}")
            return False
    else:
        print("  ❌ prometheus.yml not found")
        return False
    
    # Test alerts config
    alerts_config = monitoring_dir / "alerts.yml"
    if alerts_config.exists():
        try:
            with open(alerts_config) as f:
                alerts = yaml.safe_load(f)
            print("  ✅ Alerts configuration valid")
        except Exception as e:
            print(f"  ❌ Alerts config error: {e}")
            return False
    else:
        print("  ❌ alerts.yml not found")
        return False
    
    return True


def test_environment_config():
    """Test environment configuration."""
    print("🔧 Testing environment configuration...")
    
    env_example = Path(".env.example")
    if env_example.exists():
        env_content = env_example.read_text()
        required_vars = ['OPENAI_API_KEY', 'GITHUB_TOKEN', 'OTEL_ENABLED']
        
        for var in required_vars:
            if var in env_content:
                print(f"    ✅ {var} documented")
            else:
                print(f"    ❌ {var} missing from .env.example")
                
        print("  ✅ Environment configuration template exists")
    else:
        print("  ❌ .env.example not found")
        return False
    
    return True


def test_core_functionality():
    """Test that core agent functionality still works."""
    print("🤖 Testing core agent functionality...")
    
    try:
        from src.repo_patcher.agent.config import AgentConfig
        from src.repo_patcher.agent.state_machine import AgentStateMachine
        from src.repo_patcher.agent.models import AgentSession, RepositoryContext, AgentState
        from pathlib import Path
        
        # Test configuration
        config = AgentConfig()
        print(f"  ✅ AgentConfig loads successfully")
        
        # Test state machine
        state_machine = AgentStateMachine()
        print(f"  ✅ AgentStateMachine initializes")
        
        # Test models
        repo_context = RepositoryContext(
            repo_path=Path('/tmp'),
            repo_url='https://github.com/test/test',
            branch='main',
            commit_sha='abc123',
            test_framework='pytest',
            test_command='python -m pytest'
        )
        
        session = AgentSession(
            session_id='test-session',
            repository=repo_context,
            current_state=AgentState.IDLE
        )
        
        print(f"  ✅ AgentSession creates successfully")
        
    except Exception as e:
        print(f"  ❌ Core functionality error: {e}")
        return False
    
    return True


def main():
    """Run all verification tests."""
    print("🚀 Phase 1D Infrastructure Verification")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_health_monitoring,
        test_telemetry,
        test_metrics_server,
        test_docker_config,
        test_github_actions,
        test_monitoring_config,
        test_environment_config,
        test_core_functionality,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 1D infrastructure tests passed!")
        print("✅ Phase 1D verification complete - production ready!")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())