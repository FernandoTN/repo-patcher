"""Advanced safety features and risk assessment for Repo Patcher."""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

from .models import FixPlan, CodePatch


class RiskLevel(Enum):
    """Risk levels for code changes."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    """Approval status for changes."""
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


@dataclass
class SafetyViolation:
    """Represents a safety rule violation."""
    rule: str
    severity: RiskLevel
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class RiskAssessment:
    """Risk assessment for a set of changes."""
    overall_risk: RiskLevel
    approval_status: ApprovalStatus
    violations: List[SafetyViolation]
    metrics: Dict[str, Any]
    rationale: str


class IntelligentFileProtector:
    """Intelligent file protection system using pattern recognition."""
    
    # Critical infrastructure files that should never be modified
    CRITICAL_FILES = {
        ".github/workflows/",
        ".git/",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".env",
        ".env.production",
        ".env.local"
    }
    
    # Files that require high-level approval
    SENSITIVE_FILES = {
        "package.json",
        "pyproject.toml",
        "go.mod",
        "Cargo.toml",
        "requirements.txt",
        "setup.py",
        "tsconfig.json",
        "webpack.config.js",
        "jest.config.js"
    }
    
    # Pattern-based file detection
    SENSITIVE_PATTERNS = [
        r'.*\.env.*',           # Environment files
        r'.*secret.*',          # Secret files
        r'.*key.*\.pem',        # Key files
        r'.*\.key$',            # Key files
        r'.*config.*\.ya?ml$',  # Config files
        r'.*\.dockerfile$',     # Dockerfile variants
        r'.*kubernetes.*\.ya?ml$', # Kubernetes configs
        r'.*helm.*\.ya?ml$',    # Helm charts
        r'.*terraform.*\.tf$',  # Terraform files
        r'.*ansible.*\.ya?ml$', # Ansible playbooks
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS]
    
    def assess_file_risk(self, file_path: Path) -> RiskLevel:
        """Assess the risk level of modifying a specific file."""
        file_str = str(file_path).lower()
        
        # Check critical files
        for critical_pattern in self.CRITICAL_FILES:
            if critical_pattern in file_str:
                return RiskLevel.CRITICAL
        
        # Check sensitive files
        for sensitive_file in self.SENSITIVE_FILES:
            if file_str.endswith(sensitive_file.lower()):
                return RiskLevel.HIGH
        
        # Check pattern-based detection
        for pattern in self.compiled_patterns:
            if pattern.search(file_str):
                return RiskLevel.HIGH
        
        # Check file extension based risks
        if file_path.suffix in ['.sh', '.bash', '.ps1', '.bat']:
            return RiskLevel.MEDIUM
        
        # Test files are lower risk
        if any(test_pattern in file_str for test_pattern in ['test', 'spec', '__tests__']):
            return RiskLevel.LOW
        
        # Regular source files
        return RiskLevel.MINIMAL
    
    def is_file_protected(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a file is protected from modification."""
        file_str = str(file_path).lower()
        
        # Critical files are fully protected
        for critical_pattern in self.CRITICAL_FILES:
            if critical_pattern in file_str:
                return True, f"Critical infrastructure file: {critical_pattern}"
        
        # Check for absolute protection patterns
        absolute_protection_patterns = [
            r'.*\.git/.*',
            r'.*\.github/workflows/.*',
            r'.*dockerfile.*',
            r'.*\.env$',
            r'.*\.env\.production$'
        ]
        
        for pattern in absolute_protection_patterns:
            if re.search(pattern, file_str, re.IGNORECASE):
                return True, f"Protected by pattern: {pattern}"
        
        return False, ""


class DiffAnalyzer:
    """Analyzes code diffs for risk assessment."""
    
    HIGH_RISK_OPERATIONS = [
        'rm ', 'del ', 'delete', 'DROP TABLE', 'DROP DATABASE',
        'sudo ', 'chmod 777', 'exec(', 'eval(', 'system(',
        'os.system', 'subprocess.call', 'shell=True'
    ]
    
    MEDIUM_RISK_PATTERNS = [
        r'password\s*=',
        r'secret\s*=',
        r'token\s*=',
        r'api_key\s*=',
        r'private_key\s*=',
        r'\.execute\(',
        r'\.sql\(',
        r'import\s+os',
        r'import\s+subprocess'
    ]
    
    def __init__(self):
        self.medium_risk_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in self.MEDIUM_RISK_PATTERNS]
    
    def analyze_diff(self, patch: CodePatch) -> List[SafetyViolation]:
        """Analyze a code patch for safety violations."""
        violations = []
        
        # Check for high-risk operations
        for operation in self.HIGH_RISK_OPERATIONS:
            if operation in patch.new_content:
                violations.append(SafetyViolation(
                    rule="high_risk_operation",
                    severity=RiskLevel.HIGH,
                    message=f"High-risk operation detected: {operation}",
                    file_path=patch.file_path
                ))
        
        # Check for medium-risk patterns
        for pattern in self.medium_risk_compiled:
            if pattern.search(patch.new_content):
                violations.append(SafetyViolation(
                    rule="medium_risk_pattern",
                    severity=RiskLevel.MEDIUM,
                    message=f"Medium-risk pattern detected: {pattern.pattern}",
                    file_path=patch.file_path
                ))
        
        # Check diff size
        if patch.lines_added + patch.lines_removed > 100:
            violations.append(SafetyViolation(
                rule="large_diff",
                severity=RiskLevel.MEDIUM,
                message=f"Large diff detected: {patch.lines_added + patch.lines_removed} lines changed",
                file_path=patch.file_path
            ))
        
        # Check for potential secrets
        secret_patterns = [
            r'["\'][A-Za-z0-9+/=]{32,}["\']',  # Base64-like strings
            r'["\'][A-Za-z0-9_-]{20,}["\']',   # API keys
            r'-----BEGIN [A-Z ]+-----',         # PEM keys
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, patch.new_content):
                violations.append(SafetyViolation(
                    rule="potential_secret",
                    severity=RiskLevel.HIGH,
                    message="Potential secret or credential detected in code",
                    file_path=patch.file_path
                ))
        
        return violations


class ApprovalWorkflow:
    """Advanced approval workflow system."""
    
    def __init__(self):
        self.file_protector = IntelligentFileProtector()
        self.diff_analyzer = DiffAnalyzer()
    
    def assess_changes(self, plan: FixPlan, patches: List[CodePatch]) -> RiskAssessment:
        """Assess the risk of a set of changes and determine approval requirements."""
        violations = []
        file_risks = []
        metrics = {
            "total_files": len(patches),
            "total_lines_changed": sum(p.lines_added + p.lines_removed for p in patches),
            "protected_files": 0,
            "sensitive_files": 0
        }
        
        # Analyze each patch
        for patch in patches:
            file_path = Path(patch.file_path)
            
            # Check file protection
            is_protected, protection_reason = self.file_protector.is_file_protected(file_path)
            if is_protected:
                violations.append(SafetyViolation(
                    rule="protected_file",
                    severity=RiskLevel.CRITICAL,
                    message=f"Protected file modification blocked: {protection_reason}",
                    file_path=patch.file_path
                ))
                metrics["protected_files"] += 1
            
            # Assess file risk
            file_risk = self.file_protector.assess_file_risk(file_path)
            file_risks.append(file_risk)
            
            if file_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                metrics["sensitive_files"] += 1
            
            # Analyze diff content
            diff_violations = self.diff_analyzer.analyze_diff(patch)
            violations.extend(diff_violations)
        
        # Determine overall risk
        overall_risk = self._calculate_overall_risk(file_risks, violations, metrics, plan)
        
        # Determine approval status
        approval_status = self._determine_approval_status(overall_risk, violations, metrics)
        
        # Generate rationale
        rationale = self._generate_rationale(overall_risk, violations, metrics, plan)
        
        return RiskAssessment(
            overall_risk=overall_risk,
            approval_status=approval_status,
            violations=violations,
            metrics=metrics,
            rationale=rationale
        )
    
    def _calculate_overall_risk(self, file_risks: List[RiskLevel], violations: List[SafetyViolation], 
                              metrics: Dict[str, Any], plan: FixPlan) -> RiskLevel:
        """Calculate the overall risk level."""
        
        # If any critical violations, overall risk is critical
        if any(v.severity == RiskLevel.CRITICAL for v in violations):
            return RiskLevel.CRITICAL
        
        # If any high-risk violations or files, overall risk is high
        if (any(v.severity == RiskLevel.HIGH for v in violations) or
            any(risk == RiskLevel.HIGH for risk in file_risks)):
            return RiskLevel.HIGH
        
        # Check metrics-based risk factors
        if metrics["total_lines_changed"] > 200:
            return RiskLevel.HIGH
        elif metrics["total_lines_changed"] > 100:
            return RiskLevel.MEDIUM
        
        if metrics["sensitive_files"] > 0:
            return RiskLevel.MEDIUM
        
        # Check plan risk level
        if plan.risk_level == "high":
            return RiskLevel.HIGH
        elif plan.risk_level == "medium":
            return RiskLevel.MEDIUM
        
        # If any medium-risk violations, overall risk is medium
        if any(v.severity == RiskLevel.MEDIUM for v in violations):
            return RiskLevel.MEDIUM
        
        # Default to low risk
        return RiskLevel.LOW
    
    def _determine_approval_status(self, overall_risk: RiskLevel, violations: List[SafetyViolation], 
                                 metrics: Dict[str, Any]) -> ApprovalStatus:
        """Determine the approval status based on risk assessment."""
        
        # Critical risk or protected file violations block changes
        if (overall_risk == RiskLevel.CRITICAL or 
            any(v.severity == RiskLevel.CRITICAL for v in violations)):
            return ApprovalStatus.BLOCKED
        
        # High risk requires approval
        if overall_risk == RiskLevel.HIGH:
            return ApprovalStatus.REQUIRES_APPROVAL
        
        # Medium risk needs review
        if overall_risk == RiskLevel.MEDIUM:
            return ApprovalStatus.NEEDS_REVIEW
        
        # Low risk and minimal changes can be auto-approved
        if overall_risk in [RiskLevel.LOW, RiskLevel.MINIMAL] and metrics["total_lines_changed"] <= 20:
            return ApprovalStatus.AUTO_APPROVED
        
        return ApprovalStatus.NEEDS_REVIEW
    
    def _generate_rationale(self, overall_risk: RiskLevel, violations: List[SafetyViolation], 
                          metrics: Dict[str, Any], plan: FixPlan) -> str:
        """Generate human-readable rationale for the risk assessment."""
        
        rationale_parts = [f"Overall risk assessed as {overall_risk.value.upper()}."]
        
        # Add metrics summary
        rationale_parts.append(
            f"Changes affect {metrics['total_files']} file(s) with "
            f"{metrics['total_lines_changed']} lines modified."
        )
        
        if metrics["protected_files"] > 0:
            rationale_parts.append(f"{metrics['protected_files']} protected file(s) detected.")
        
        if metrics["sensitive_files"] > 0:
            rationale_parts.append(f"{metrics['sensitive_files']} sensitive file(s) affected.")
        
        # Add violation summary
        if violations:
            violation_counts = {}
            for violation in violations:
                violation_counts[violation.severity] = violation_counts.get(violation.severity, 0) + 1
            
            violation_summary = []
            for severity, count in violation_counts.items():
                violation_summary.append(f"{count} {severity.value}")
            
            rationale_parts.append(f"Safety violations: {', '.join(violation_summary)}.")
        
        # Add plan context
        if plan.total_confidence < 0.7:
            rationale_parts.append(f"Plan confidence is low ({plan.total_confidence:.1%}).")
        
        return " ".join(rationale_parts)


class SafetyEnforcer:
    """Main safety enforcement system."""
    
    def __init__(self):
        self.approval_workflow = ApprovalWorkflow()
        self._blocked_changes_log = []
    
    def validate_changes(self, plan: FixPlan, patches: List[CodePatch]) -> RiskAssessment:
        """Validate a set of changes and return risk assessment."""
        return self.approval_workflow.assess_changes(plan, patches)
    
    def is_safe_to_proceed(self, risk_assessment: RiskAssessment) -> bool:
        """Determine if it's safe to proceed with changes."""
        return risk_assessment.approval_status != ApprovalStatus.BLOCKED
    
    def requires_human_approval(self, risk_assessment: RiskAssessment) -> bool:
        """Determine if changes require human approval."""
        return risk_assessment.approval_status in [
            ApprovalStatus.REQUIRES_APPROVAL,
            ApprovalStatus.NEEDS_REVIEW
        ]
    
    def log_blocked_change(self, risk_assessment: RiskAssessment, session_id: str) -> None:
        """Log a blocked change for audit purposes."""
        self._blocked_changes_log.append({
            "session_id": session_id,
            "risk_level": risk_assessment.overall_risk.value,
            "violations": len(risk_assessment.violations),
            "rationale": risk_assessment.rationale,
            "timestamp": hash(f"{session_id}{risk_assessment.rationale}")  # Simple timestamp hash
        })
    
    def get_safety_summary(self) -> Dict[str, Any]:
        """Get a summary of safety enforcement activities."""
        return {
            "blocked_changes": len(self._blocked_changes_log),
            "recent_blocks": self._blocked_changes_log[-10:] if self._blocked_changes_log else []
        }