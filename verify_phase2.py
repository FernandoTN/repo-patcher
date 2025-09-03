#!/usr/bin/env python3
"""
Phase 2 Verification Script for Repo Patcher

This script verifies that all Phase 2 components are properly implemented and functional.
It tests multi-language support, safety features, and performance optimization.
"""

import sys
import os
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback
from datetime import datetime


class Phase2Verifier:
    """Comprehensive verification of Phase 2 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.repo_root = Path(__file__).parent
        sys.path.insert(0, str(self.repo_root / "src"))
        
    def log_test(self, test_name: str, status: str, details: str = "", error: Optional[str] = None) -> None:
        """Log a test result."""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
    
    def test_imports(self) -> None:
        """Test that all new Phase 2 modules can be imported."""
        print("\n🧪 Testing Phase 2 Module Imports...")
        
        # Test language support imports
        try:
            from repo_patcher.tools.language_support import (
                Language, TestFramework, LanguageDetector, MultiLanguageTestRunner
            )
            from repo_patcher.tools.javascript_handler import JavaScriptHandler
            from repo_patcher.tools.python_handler import PythonHandler  
            from repo_patcher.tools.go_handler import GoHandler
            self.log_test("Language Support Imports", "PASSED", "All language support modules imported successfully")
        except ImportError as e:
            self.log_test("Language Support Imports", "FAILED", error=str(e))
        
        # Test safety features imports
        try:
            from repo_patcher.agent.safety import (
                IntelligentFileProtector, DiffAnalyzer, ApprovalWorkflow, SafetyEnforcer
            )
            self.log_test("Safety Features Imports", "PASSED", "All safety modules imported successfully")
        except ImportError as e:
            self.log_test("Safety Features Imports", "FAILED", error=str(e))
        
        # Test performance optimization imports
        try:
            from repo_patcher.agent.performance import (
                IntelligentCache, CostOptimizer, PerformanceOptimizer
            )
            self.log_test("Performance Optimization Imports", "PASSED", "All performance modules imported successfully")
        except ImportError as e:
            self.log_test("Performance Optimization Imports", "FAILED", error=str(e))
    
    def test_language_detection(self) -> None:
        """Test language detection functionality."""
        print("\n🌐 Testing Language Detection...")
        
        try:
            from repo_patcher.tools.language_support import LanguageDetector, Language
            
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir)
                
                # Test Python detection
                (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
                (repo_path / "src" / "main.py").parent.mkdir(exist_ok=True)
                (repo_path / "src" / "main.py").write_text("def main(): pass")
                
                language = LanguageDetector.detect_language(repo_path)
                if language == Language.PYTHON:
                    self.log_test("Python Language Detection", "PASSED", "Correctly detected Python project")
                else:
                    self.log_test("Python Language Detection", "FAILED", f"Expected Python, got {language}")
                
                # Test JavaScript detection
                (repo_path / "pyproject.toml").unlink()
                (repo_path / "src" / "main.py").unlink()
                (repo_path / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
                (repo_path / "src" / "index.js").write_text("console.log('test');")
                
                language = LanguageDetector.detect_language(repo_path)
                if language == Language.JAVASCRIPT:
                    self.log_test("JavaScript Language Detection", "PASSED", "Correctly detected JavaScript project")
                else:
                    self.log_test("JavaScript Language Detection", "FAILED", f"Expected JavaScript, got {language}")
        
        except Exception as e:
            self.log_test("Language Detection", "FAILED", error=str(e))
    
    def test_test_runner_integration(self) -> None:
        """Test enhanced test runner with multi-language support."""
        print("\n🧪 Testing Multi-Language Test Runner...")
        
        try:
            from repo_patcher.tools.test_runner import TestRunnerTool
            
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir)
                
                # Create a simple Python project
                (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
                (repo_path / "tests").mkdir()
                (repo_path / "tests" / "test_sample.py").write_text("""
def test_sample():
    assert True
""")
                
                runner = TestRunnerTool()
                analysis = runner.analyze_repository(repo_path)
                
                if analysis.get("language") == "python" and analysis.get("framework") == "pytest":
                    self.log_test("Multi-Language Test Runner", "PASSED", 
                                f"Successfully analyzed Python project: {analysis}")
                else:
                    self.log_test("Multi-Language Test Runner", "FAILED", 
                                f"Unexpected analysis result: {analysis}")
        
        except Exception as e:
            self.log_test("Multi-Language Test Runner", "FAILED", error=str(e))
    
    def test_safety_features(self) -> None:
        """Test safety and security features."""
        print("\n🛡️ Testing Safety Features...")
        
        try:
            from repo_patcher.agent.safety import IntelligentFileProtector, SafetyEnforcer, RiskLevel
            from repo_patcher.agent.models import FixPlan, CodePatch, PlanStep
            
            # Test file protection
            protector = IntelligentFileProtector()
            
            # Test critical file detection
            critical_files = [
                Path(".github/workflows/ci.yml"),
                Path("Dockerfile"), 
                Path(".env")
            ]
            
            for file_path in critical_files:
                risk = protector.assess_file_risk(file_path)
                if risk == RiskLevel.CRITICAL:
                    self.log_test(f"Critical File Protection ({file_path})", "PASSED", 
                                f"Correctly identified as {risk.value} risk")
                else:
                    self.log_test(f"Critical File Protection ({file_path})", "FAILED", 
                                f"Expected CRITICAL, got {risk.value}")
            
            # Test safety enforcer
            enforcer = SafetyEnforcer()
            
            # Create a safe change
            safe_plan = FixPlan(
                summary="Add import",
                steps=[PlanStep("Add import", "src/test.py", "modify", "Safe change", 0.9)],
                estimated_iterations=1,
                risk_level="low",
                total_confidence=0.9
            )
            
            safe_patch = CodePatch(
                file_path="src/test.py",
                old_content="def test(): pass",
                new_content="import os\ndef test(): pass",
                diff="+ import os",
                reasoning="Add import",
                lines_added=1,
                lines_removed=0,
                lines_modified=0
            )
            
            assessment = enforcer.validate_changes(safe_plan, [safe_patch])
            
            if enforcer.is_safe_to_proceed(assessment):
                self.log_test("Safety Enforcer - Safe Changes", "PASSED", 
                            f"Correctly approved safe change: {assessment.approval_status.value}")
            else:
                self.log_test("Safety Enforcer - Safe Changes", "FAILED", 
                            f"Incorrectly blocked safe change: {assessment.approval_status.value}")
        
        except Exception as e:
            self.log_test("Safety Features", "FAILED", error=str(e))
    
    def test_performance_optimization(self) -> None:
        """Test performance optimization features."""
        print("\n⚡ Testing Performance Optimization...")
        
        try:
            from repo_patcher.agent.performance import (
                PerformanceOptimizer, IntelligentCache, CacheType, OptimizationLevel
            )
            
            # Test caching system
            optimizer = PerformanceOptimizer(OptimizationLevel.BALANCED)
            
            # Test cache operations
            test_data = {"analysis": "test"}
            optimizer.set_cache(CacheType.REPOSITORY_ANALYSIS, "test_repo", test_data)
            
            cached_result = optimizer.get_from_cache(CacheType.REPOSITORY_ANALYSIS, "test_repo")
            
            if cached_result == test_data:
                self.log_test("Performance Caching", "PASSED", 
                            f"Cache hit ratio: {optimizer.metrics.cache_hit_ratio:.1%}")
            else:
                self.log_test("Performance Caching", "FAILED", 
                            f"Cache miss: expected {test_data}, got {cached_result}")
            
            # Test cost optimization
            from repo_patcher.agent.performance import CostOptimizer
            cost_optimizer = CostOptimizer()
            
            # Test model recommendation
            model = cost_optimizer.recommend_model("simple", current_cost=0.10, budget_remaining=0.40)
            if model in ["gpt-4o", "gpt-4o-mini"]:
                self.log_test("Cost Optimization", "PASSED", f"Recommended model: {model}")
            else:
                self.log_test("Cost Optimization", "FAILED", f"Unexpected model recommendation: {model}")
        
        except Exception as e:
            self.log_test("Performance Optimization", "FAILED", error=str(e))
    
    def test_scenarios(self) -> None:
        """Test that Phase 2 scenarios are properly structured."""
        print("\n📋 Testing Phase 2 Scenarios...")
        
        # Test JavaScript scenario
        js_scenario_path = self.repo_root / "scenarios" / "E002_js_missing_import"
        if js_scenario_path.exists():
            scenario_file = js_scenario_path / "scenario.json"
            if scenario_file.exists():
                try:
                    with open(scenario_file) as f:
                        scenario = json.load(f)
                    
                    if (scenario.get("language") == "javascript" and 
                        scenario.get("test_framework") == "jest"):
                        self.log_test("JavaScript Scenario Structure", "PASSED", 
                                    f"E002 scenario properly configured: {scenario['name']}")
                    else:
                        self.log_test("JavaScript Scenario Structure", "FAILED", 
                                    f"Incorrect scenario configuration: {scenario}")
                except Exception as e:
                    self.log_test("JavaScript Scenario Structure", "FAILED", error=str(e))
            else:
                self.log_test("JavaScript Scenario Structure", "FAILED", 
                            "Missing scenario.json file")
        else:
            self.log_test("JavaScript Scenario Structure", "FAILED", 
                        "E002_js_missing_import directory not found")
        
        # Test Go scenario
        go_scenario_path = self.repo_root / "scenarios" / "E003_go_missing_import"
        if go_scenario_path.exists():
            scenario_file = go_scenario_path / "scenario.json"
            if scenario_file.exists():
                try:
                    with open(scenario_file) as f:
                        scenario = json.load(f)
                    
                    if (scenario.get("language") == "go" and 
                        scenario.get("test_framework") == "go_test"):
                        self.log_test("Go Scenario Structure", "PASSED", 
                                    f"E003 scenario properly configured: {scenario['name']}")
                    else:
                        self.log_test("Go Scenario Structure", "FAILED", 
                                    f"Incorrect scenario configuration: {scenario}")
                except Exception as e:
                    self.log_test("Go Scenario Structure", "FAILED", error=str(e))
            else:
                self.log_test("Go Scenario Structure", "FAILED", "Missing scenario.json file")
        else:
            self.log_test("Go Scenario Structure", "FAILED", 
                        "E003_go_missing_import directory not found")
    
    def test_existing_functionality(self) -> None:
        """Test that existing Phase 1 functionality still works."""
        print("\n🔄 Testing Backward Compatibility...")
        
        try:
            # Test that existing evaluation framework still works
            from repo_patcher.evaluation.runner import EvaluationRunner
            from repo_patcher.evaluation.models import ScenarioMetadata
            
            # Test that existing scenario still loads
            e001_path = self.repo_root / "scenarios" / "E001_missing_import"
            if e001_path.exists():
                scenario_file = e001_path / "scenario.json"
                if scenario_file.exists():
                    with open(scenario_file) as f:
                        scenario_data = json.load(f)
                    
                    if scenario_data.get("language") == "python":
                        self.log_test("Backward Compatibility", "PASSED", 
                                    "E001 Python scenario still functional")
                    else:
                        self.log_test("Backward Compatibility", "FAILED", 
                                    f"E001 scenario modified incorrectly: {scenario_data}")
                else:
                    self.log_test("Backward Compatibility", "FAILED", "E001 scenario.json missing")
            else:
                self.log_test("Backward Compatibility", "FAILED", "E001 scenario directory missing")
        
        except Exception as e:
            self.log_test("Backward Compatibility", "FAILED", error=str(e))
    
    def run_unit_tests(self) -> None:
        """Run the Phase 2 unit tests."""
        print("\n🧪 Running Phase 2 Unit Tests...")
        
        test_files = [
            "tests/test_phase2_multi_language.py",
            "tests/test_phase2_safety.py", 
            "tests/test_phase2_performance.py"
        ]
        
        for test_file in test_files:
            test_path = self.repo_root / test_file
            if test_path.exists():
                try:
                    # Run pytest on the specific test file
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"
                    ], cwd=self.repo_root, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        self.log_test(f"Unit Tests ({test_file})", "PASSED", 
                                    "All tests in file passed")
                    else:
                        self.log_test(f"Unit Tests ({test_file})", "FAILED", 
                                    details=result.stdout[-500:],  # Last 500 chars
                                    error=result.stderr[-500:])
                
                except subprocess.TimeoutExpired:
                    self.log_test(f"Unit Tests ({test_file})", "FAILED", 
                                error="Test execution timed out")
                except Exception as e:
                    self.log_test(f"Unit Tests ({test_file})", "FAILED", error=str(e))
            else:
                self.log_test(f"Unit Tests ({test_file})", "FAILED", 
                            f"Test file not found: {test_file}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive verification report."""
        passed_tests = [t for t in self.test_results if t["status"] == "PASSED"]
        failed_tests = [t for t in self.test_results if t["status"] == "FAILED"]
        warning_tests = [t for t in self.test_results if t["status"] == "WARNING"]
        
        report = {
            "verification_date": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "warning_tests": len(warning_tests),
            "success_rate": len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0,
            "overall_status": "PASSED" if len(failed_tests) == 0 else "FAILED",
            "test_results": self.test_results
        }
        
        return report
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Phase 2 verification tests."""
        print("🚀 Starting Phase 2 Verification...")
        print("=" * 60)
        
        # Run all test categories
        self.test_imports()
        self.test_language_detection()
        self.test_test_runner_integration()
        self.test_safety_features()
        self.test_performance_optimization()
        self.test_scenarios()
        self.test_existing_functionality()
        self.run_unit_tests()
        
        # Generate and display report
        report = self.generate_report()
        
        print("\n" + "=" * 60)
        print("📊 PHASE 2 VERIFICATION REPORT")
        print("=" * 60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']} ✅")
        print(f"Failed: {report['failed_tests']} ❌")
        print(f"Warnings: {report['warning_tests']} ⚠️")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        print(f"Overall Status: {report['overall_status']}")
        
        if report['failed_tests'] > 0:
            print(f"\n❌ FAILED TESTS ({report['failed_tests']}):")
            for test in self.test_results:
                if test["status"] == "FAILED":
                    print(f"  • {test['test']}: {test.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 60)
        
        # Save detailed report
        report_file = self.repo_root / "PHASE_2_VERIFICATION_REPORT.md"
        self.save_detailed_report(report, report_file)
        print(f"📄 Detailed report saved to: {report_file}")
        
        return report
    
    def save_detailed_report(self, report: Dict[str, Any], file_path: Path) -> None:
        """Save a detailed markdown report."""
        with open(file_path, 'w') as f:
            f.write("# Phase 2 Verification Report\n\n")
            f.write(f"**Date**: {report['verification_date']}\n")
            f.write(f"**Overall Status**: {'✅ PASSED' if report['overall_status'] == 'PASSED' else '❌ FAILED'}\n")
            f.write(f"**Success Rate**: {report['success_rate']:.1f}%\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests**: {report['total_tests']}\n")
            f.write(f"- **Passed**: {report['passed_tests']} ✅\n") 
            f.write(f"- **Failed**: {report['failed_tests']} ❌\n")
            f.write(f"- **Warnings**: {report['warning_tests']} ⚠️\n\n")
            
            f.write("## Detailed Results\n\n")
            
            for test in self.test_results:
                status_emoji = {"PASSED": "✅", "FAILED": "❌", "WARNING": "⚠️"}.get(test["status"], "❓")
                f.write(f"### {status_emoji} {test['test']}\n")
                f.write(f"**Status**: {test['status']}\n")
                if test.get('details'):
                    f.write(f"**Details**: {test['details']}\n")
                if test.get('error'):
                    f.write(f"**Error**: {test['error']}\n")
                f.write(f"**Timestamp**: {test['timestamp']}\n\n")
            
            if report['overall_status'] == 'PASSED':
                f.write("## ✅ Phase 2 Verification Successful\n\n")
                f.write("All Phase 2 components have been successfully verified and are ready for production testing.\n")
            else:
                f.write("## ❌ Phase 2 Verification Failed\n\n")
                f.write("Some Phase 2 components failed verification. Please review the failed tests and fix the issues before proceeding.\n")


def main():
    """Main verification entry point."""
    verifier = Phase2Verifier()
    
    try:
        report = verifier.run_all_tests()
        
        # Exit with appropriate code
        if report['overall_status'] == 'PASSED':
            print("\n🎉 Phase 2 verification completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ Phase 2 verification failed with {report['failed_tests']} failed tests.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n💥 Verification script failed with error: {str(e)}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()