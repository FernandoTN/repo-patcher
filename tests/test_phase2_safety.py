"""Tests for Phase 2 advanced safety features."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.repo_patcher.agent.safety import (
    IntelligentFileProtector, DiffAnalyzer, ApprovalWorkflow, SafetyEnforcer,
    RiskLevel, ApprovalStatus, SafetyViolation, RiskAssessment
)
from src.repo_patcher.agent.models import FixPlan, CodePatch, PlanStep


class TestIntelligentFileProtector:
    """Test the intelligent file protection system."""
    
    def test_assess_critical_file_risk(self):
        """Test risk assessment for critical files."""
        protector = IntelligentFileProtector()
        
        critical_files = [
            Path(".github/workflows/ci.yml"),
            Path("Dockerfile"),
            Path(".env"),
            Path("docker-compose.yml")
        ]
        
        for file_path in critical_files:
            risk = protector.assess_file_risk(file_path)
            assert risk == RiskLevel.CRITICAL, f"File {file_path} should be CRITICAL risk"
    
    def test_assess_sensitive_file_risk(self):
        """Test risk assessment for sensitive files."""
        protector = IntelligentFileProtector()
        
        sensitive_files = [
            Path("package.json"),
            Path("pyproject.toml"),
            Path("go.mod"),
            Path("requirements.txt")
        ]
        
        for file_path in sensitive_files:
            risk = protector.assess_file_risk(file_path)
            assert risk == RiskLevel.HIGH, f"File {file_path} should be HIGH risk"
    
    def test_assess_test_file_risk(self):
        """Test risk assessment for test files."""
        protector = IntelligentFileProtector()
        
        test_files = [
            Path("tests/test_calculator.py"),
            Path("__tests__/utils.test.js"),
            Path("src/component.spec.ts")
        ]
        
        for file_path in test_files:
            risk = protector.assess_file_risk(file_path)
            assert risk == RiskLevel.LOW, f"Test file {file_path} should be LOW risk"
    
    def test_assess_regular_file_risk(self):
        """Test risk assessment for regular source files."""
        protector = IntelligentFileProtector()
        
        regular_files = [
            Path("src/calculator.py"),
            Path("lib/utils.js"),
            Path("internal/handler.go")
        ]
        
        for file_path in regular_files:
            risk = protector.assess_file_risk(file_path)
            assert risk == RiskLevel.MINIMAL, f"Regular file {file_path} should be MINIMAL risk"
    
    def test_is_file_protected(self):
        """Test file protection detection."""
        protector = IntelligentFileProtector()
        
        # Critical files should be protected
        is_protected, reason = protector.is_file_protected(Path(".github/workflows/ci.yml"))
        assert is_protected
        assert "Critical infrastructure file" in reason
        
        # Regular files should not be protected
        is_protected, reason = protector.is_file_protected(Path("src/main.py"))
        assert not is_protected
        assert reason == ""
    
    def test_pattern_based_protection(self):
        """Test pattern-based file protection."""
        protector = IntelligentFileProtector()
        
        pattern_files = [
            Path("config/secrets.yaml"),
            Path("deploy/production.env"),
            Path("certs/private.key"),
            Path("k8s/deployment.yaml")
        ]
        
        for file_path in pattern_files:
            risk = protector.assess_file_risk(file_path)
            assert risk == RiskLevel.HIGH, f"Pattern file {file_path} should be HIGH risk"


class TestDiffAnalyzer:
    """Test the diff analyzer for safety violations."""
    
    def test_detect_high_risk_operations(self):
        """Test detection of high-risk operations."""
        analyzer = DiffAnalyzer()
        
        dangerous_patch = CodePatch(
            file_path="src/utils.py",
            old_content="def safe_function(): pass",
            new_content="import os\nos.system('rm -rf /')",
            diff="+ os.system('rm -rf /')",
            reasoning="Adding dangerous operation",
            lines_added=1,
            lines_removed=0,
            lines_modified=0
        )
        
        violations = analyzer.analyze_diff(dangerous_patch)
        
        # Should detect high-risk operation
        high_risk_violations = [v for v in violations if v.severity == RiskLevel.HIGH]
        assert len(high_risk_violations) > 0
        assert any("High-risk operation" in v.message for v in high_risk_violations)
    
    def test_detect_potential_secrets(self):
        """Test detection of potential secrets in code."""
        analyzer = DiffAnalyzer()
        
        secret_patch = CodePatch(
            file_path="src/config.py",
            old_content="API_KEY = None",
            new_content='API_KEY = "sk-1234567890abcdef1234567890abcdef"',
            diff='+ API_KEY = "sk-1234567890abcdef1234567890abcdef"',
            reasoning="Adding API key",
            lines_added=1,
            lines_removed=0,
            lines_modified=0
        )
        
        violations = analyzer.analyze_diff(secret_patch)
        
        # Should detect potential secret
        secret_violations = [v for v in violations if "secret" in v.message.lower()]
        assert len(secret_violations) > 0
    
    def test_detect_large_diff(self):
        """Test detection of large diffs."""
        analyzer = DiffAnalyzer()
        
        large_patch = CodePatch(
            file_path="src/large_file.py",
            old_content="# Old content",
            new_content="# New content with many lines",
            diff="Large diff with many changes",
            reasoning="Major refactoring",
            lines_added=150,
            lines_removed=50,
            lines_modified=0
        )
        
        violations = analyzer.analyze_diff(large_patch)
        
        # Should detect large diff
        large_diff_violations = [v for v in violations if "Large diff" in v.message]
        assert len(large_diff_violations) > 0
        assert large_diff_violations[0].severity == RiskLevel.MEDIUM
    
    def test_detect_medium_risk_patterns(self):
        """Test detection of medium-risk patterns."""
        analyzer = DiffAnalyzer()
        
        risky_patch = CodePatch(
            file_path="src/auth.py",
            old_content="def authenticate(): pass",
            new_content="def authenticate():\n    password = 'secret123'",
            diff="+ password = 'secret123'",
            reasoning="Adding password handling",
            lines_added=1,
            lines_removed=0,
            lines_modified=0
        )
        
        violations = analyzer.analyze_diff(risky_patch)
        
        # Should detect medium-risk pattern
        medium_risk_violations = [v for v in violations if v.severity == RiskLevel.MEDIUM]
        assert len(medium_risk_violations) > 0


class TestApprovalWorkflow:
    """Test the approval workflow system."""
    
    def create_sample_plan(self, risk_level: str = "low") -> FixPlan:
        """Create a sample fix plan for testing."""
        return FixPlan(
            summary="Fix missing import",
            steps=[
                PlanStep(
                    description="Add import statement",
                    file_path="src/calculator.py",
                    change_type="modify",
                    reasoning="Need to import sqrt function",
                    confidence=0.9
                )
            ],
            estimated_iterations=1,
            risk_level=risk_level,
            total_confidence=0.9
        )
    
    def create_sample_patch(self, file_path: str = "src/calculator.py", lines_changed: int = 1) -> CodePatch:
        """Create a sample code patch for testing."""
        return CodePatch(
            file_path=file_path,
            old_content="def sqrt_calc(x): return sqrt(x)",
            new_content="from math import sqrt\ndef sqrt_calc(x): return sqrt(x)",
            diff="+ from math import sqrt",
            reasoning="Add missing import",
            lines_added=lines_changed,
            lines_removed=0,
            lines_modified=0
        )
    
    def test_assess_low_risk_changes(self):
        """Test assessment of low-risk changes."""
        workflow = ApprovalWorkflow()
        
        plan = self.create_sample_plan("low")
        patches = [self.create_sample_patch()]
        
        assessment = workflow.assess_changes(plan, patches)
        
        assert assessment.overall_risk in [RiskLevel.LOW, RiskLevel.MINIMAL]
        assert assessment.approval_status == ApprovalStatus.AUTO_APPROVED
        assert len(assessment.violations) == 0
    
    def test_assess_high_risk_changes(self):
        """Test assessment of high-risk changes."""
        workflow = ApprovalWorkflow()
        
        plan = self.create_sample_plan("high")
        patches = [self.create_sample_patch("package.json", 50)]  # Sensitive file with many changes
        
        assessment = workflow.assess_changes(plan, patches)
        
        assert assessment.overall_risk == RiskLevel.HIGH
        assert assessment.approval_status in [ApprovalStatus.REQUIRES_APPROVAL, ApprovalStatus.NEEDS_REVIEW]
        assert assessment.metrics["sensitive_files"] > 0
    
    def test_assess_protected_file_changes(self):
        """Test assessment of changes to protected files."""
        workflow = ApprovalWorkflow()
        
        plan = self.create_sample_plan("medium")
        patches = [self.create_sample_patch(".github/workflows/ci.yml")]
        
        assessment = workflow.assess_changes(plan, patches)
        
        assert assessment.overall_risk == RiskLevel.CRITICAL
        assert assessment.approval_status == ApprovalStatus.BLOCKED
        
        # Should have critical violations
        critical_violations = [v for v in assessment.violations if v.severity == RiskLevel.CRITICAL]
        assert len(critical_violations) > 0
    
    def test_assess_large_diff_changes(self):
        """Test assessment of large diff changes."""
        workflow = ApprovalWorkflow()
        
        plan = self.create_sample_plan("medium")
        patches = [self.create_sample_patch("src/large_module.py", 250)]  # Very large change
        
        assessment = workflow.assess_changes(plan, patches)
        
        assert assessment.overall_risk == RiskLevel.HIGH
        assert assessment.approval_status == ApprovalStatus.REQUIRES_APPROVAL
        assert assessment.metrics["total_lines_changed"] == 250
    
    def test_rationale_generation(self):
        """Test generation of human-readable rationale."""
        workflow = ApprovalWorkflow()
        
        plan = self.create_sample_plan("medium")
        patches = [
            self.create_sample_patch("package.json", 10),
            self.create_sample_patch("src/utils.js", 5)
        ]
        
        assessment = workflow.assess_changes(plan, patches)
        
        assert assessment.rationale
        assert "2 file(s)" in assessment.rationale
        assert "15 lines modified" in assessment.rationale
        assert assessment.overall_risk.value.upper() in assessment.rationale


class TestSafetyEnforcer:
    """Test the main safety enforcement system."""
    
    def create_sample_data(self):
        """Create sample plan and patches for testing."""
        plan = FixPlan(
            summary="Fix missing import",
            steps=[
                PlanStep(
                    description="Add import",
                    file_path="src/calculator.py",
                    change_type="modify",
                    reasoning="Missing import",
                    confidence=0.9
                )
            ],
            estimated_iterations=1,
            risk_level="low",
            total_confidence=0.9
        )
        
        patches = [
            CodePatch(
                file_path="src/calculator.py",
                old_content="def calc(): return sqrt(4)",
                new_content="from math import sqrt\ndef calc(): return sqrt(4)",
                diff="+ from math import sqrt",
                reasoning="Add import",
                lines_added=1,
                lines_removed=0,
                lines_modified=0
            )
        ]
        
        return plan, patches
    
    def test_validate_safe_changes(self):
        """Test validation of safe changes."""
        enforcer = SafetyEnforcer()
        plan, patches = self.create_sample_data()
        
        assessment = enforcer.validate_changes(plan, patches)
        
        assert enforcer.is_safe_to_proceed(assessment)
        assert not enforcer.requires_human_approval(assessment)
    
    def test_validate_dangerous_changes(self):
        """Test validation of dangerous changes."""
        enforcer = SafetyEnforcer()
        
        # Create dangerous patch
        dangerous_plan = FixPlan(
            summary="Dangerous change",
            steps=[],
            estimated_iterations=1,
            risk_level="critical",
            total_confidence=0.5
        )
        
        dangerous_patches = [
            CodePatch(
                file_path=".github/workflows/ci.yml",  # Protected file
                old_content="name: CI",
                new_content="name: CI\n# Malicious change",
                diff="+ # Malicious change",
                reasoning="Modify CI",
                lines_added=1,
                lines_removed=0,
                lines_modified=0
            )
        ]
        
        assessment = enforcer.validate_changes(dangerous_plan, dangerous_patches)
        
        assert not enforcer.is_safe_to_proceed(assessment)
        assert assessment.approval_status == ApprovalStatus.BLOCKED
    
    def test_log_blocked_change(self):
        """Test logging of blocked changes."""
        enforcer = SafetyEnforcer()
        
        # Create blocked assessment
        blocked_assessment = RiskAssessment(
            overall_risk=RiskLevel.CRITICAL,
            approval_status=ApprovalStatus.BLOCKED,
            violations=[
                SafetyViolation(
                    rule="protected_file",
                    severity=RiskLevel.CRITICAL,
                    message="Protected file modification",
                    file_path=".github/workflows/ci.yml"
                )
            ],
            metrics={"total_files": 1},
            rationale="Critical file modification blocked"
        )
        
        session_id = "test_session_123"
        enforcer.log_blocked_change(blocked_assessment, session_id)
        
        summary = enforcer.get_safety_summary()
        assert summary["blocked_changes"] == 1
        assert len(summary["recent_blocks"]) == 1
        assert summary["recent_blocks"][0]["session_id"] == session_id
    
    def test_requires_human_approval(self):
        """Test detection of changes requiring human approval."""
        enforcer = SafetyEnforcer()
        
        # High-risk assessment
        high_risk_assessment = RiskAssessment(
            overall_risk=RiskLevel.HIGH,
            approval_status=ApprovalStatus.REQUIRES_APPROVAL,
            violations=[],
            metrics={"total_files": 1, "total_lines_changed": 200},
            rationale="Large change requires approval"
        )
        
        assert enforcer.requires_human_approval(high_risk_assessment)
        
        # Medium-risk assessment
        medium_risk_assessment = RiskAssessment(
            overall_risk=RiskLevel.MEDIUM,
            approval_status=ApprovalStatus.NEEDS_REVIEW,
            violations=[],
            metrics={"total_files": 1, "total_lines_changed": 50},
            rationale="Medium risk needs review"
        )
        
        assert enforcer.requires_human_approval(medium_risk_assessment)
        
        # Low-risk assessment
        low_risk_assessment = RiskAssessment(
            overall_risk=RiskLevel.LOW,
            approval_status=ApprovalStatus.AUTO_APPROVED,
            violations=[],
            metrics={"total_files": 1, "total_lines_changed": 5},
            rationale="Low risk auto-approved"
        )
        
        assert not enforcer.requires_human_approval(low_risk_assessment)


class TestIntegration:
    """Integration tests for safety features."""
    
    def test_end_to_end_safety_workflow(self):
        """Test complete safety workflow from plan to assessment."""
        enforcer = SafetyEnforcer()
        
        # Create a realistic scenario
        plan = FixPlan(
            summary="Fix import error in multiple files",
            steps=[
                PlanStep(
                    description="Add missing import to calculator.py",
                    file_path="src/calculator.py",
                    change_type="modify",
                    reasoning="Missing math import",
                    confidence=0.95
                ),
                PlanStep(
                    description="Update package.json version",
                    file_path="package.json",
                    change_type="modify",
                    reasoning="Increment version",
                    confidence=0.8
                )
            ],
            estimated_iterations=1,
            risk_level="medium",
            total_confidence=0.875
        )
        
        patches = [
            # Safe change to source file
            CodePatch(
                file_path="src/calculator.py",
                old_content="def sqrt_calc(x): return sqrt(x)",
                new_content="from math import sqrt\ndef sqrt_calc(x): return sqrt(x)",
                diff="+ from math import sqrt",
                reasoning="Add missing import",
                lines_added=1,
                lines_removed=0,
                lines_modified=0
            ),
            # Risky change to sensitive file
            CodePatch(
                file_path="package.json",
                old_content='{"version": "1.0.0"}',
                new_content='{"version": "1.0.1"}',
                diff='- "version": "1.0.0"\n+ "version": "1.0.1"',
                reasoning="Update version",
                lines_added=1,
                lines_removed=1,
                lines_modified=0
            )
        ]
        
        # Validate the changes
        assessment = enforcer.validate_changes(plan, patches)
        
        # Should require review due to sensitive file modification
        assert assessment.overall_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert assessment.approval_status in [ApprovalStatus.NEEDS_REVIEW, ApprovalStatus.REQUIRES_APPROVAL]
        assert assessment.metrics["sensitive_files"] > 0
        assert assessment.metrics["total_files"] == 2
        assert "package.json" in str(assessment.violations) or assessment.metrics["sensitive_files"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])