"""Tool for running tests in repositories."""
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseTool
from ..evaluation.models import ExecutionStatus, TestExecution


class TestRunnerTool(BaseTool):
    """Tool for executing test suites and parsing results."""
    
    def __init__(self):
        super().__init__("run_tests")
    
    async def _execute(self, 
                      repo_path: Path, 
                      test_command: str,
                      timeout: int = 60) -> TestExecution:
        """Execute tests and return structured results."""
        
        # Use the existing test execution logic from evaluation framework
        result = subprocess.run(
            test_command.split(),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Parse pytest output to count passed/failed tests
        stdout_lines = result.stdout.split('\n')
        tests_passed = 0
        tests_failed = 0
        error_message = None
        
        for line in stdout_lines:
            if " passed" in line and " failed" in line:
                # Line like "1 failed, 3 passed in 0.02s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed,":
                        tests_failed = int(parts[i-1])
                    elif part == "passed":
                        tests_passed = int(parts[i-1])
            elif " passed in " in line:
                # Line like "4 passed in 0.01s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        tests_passed = int(parts[i-1])
            elif " failed in " in line:
                # Line like "1 failed in 0.02s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed":
                        tests_failed = int(parts[i-1])

        # Extract error message
        if result.returncode != 0:
            if result.stderr:
                error_message = result.stderr.strip()
            else:
                # Look for error in stdout
                for line in stdout_lines:
                    if "Error:" in line or "NameError:" in line or "ImportError:" in line:
                        error_message = line.strip()
                        break

        test_result = ExecutionStatus.PASSED if result.returncode == 0 else ExecutionStatus.FAILED
        
        return TestExecution(
            result=test_result,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=0.0,  # We don't track duration here since it's handled by the base class
            exit_code=result.returncode,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            error_message=error_message
        )
    
    def detect_test_framework(self, repo_path: Path) -> str:
        """Detect the test framework used in the repository."""
        # Check for common test configuration files
        if (repo_path / "pyproject.toml").exists():
            # Check for pytest in pyproject.toml
            return "pytest"
        elif (repo_path / "package.json").exists():
            # JavaScript project - likely jest
            return "jest"
        elif (repo_path / "go.mod").exists():
            return "go test"
        elif (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            return "junit"
        else:
            # Default to pytest for Python projects
            return "pytest"
    
    def get_test_command(self, repo_path: Path, framework: str) -> str:
        """Get the appropriate test command for the framework."""
        commands = {
            "pytest": "python -m pytest tests/ -v",
            "jest": "npm test",
            "go test": "go test ./...",
            "junit": "mvn test"
        }
        return commands.get(framework, "python -m pytest tests/ -v")


class CodeSearchTool(BaseTool):
    """Tool for searching code in repositories."""
    
    def __init__(self):
        super().__init__("search_code")
    
    async def _execute(self,
                      repo_path: Path,
                      query: str,
                      file_types: List[str] = None) -> Dict[str, List[str]]:
        """Search for code patterns in the repository."""
        # TODO: Implement semantic code search
        # For now, return mock data
        return {
            "matches": [],
            "files": [],
            "contexts": []
        }


class PatchApplyTool(BaseTool):
    """Tool for applying code patches safely."""
    
    def __init__(self):
        super().__init__("apply_patch")
    
    async def _execute(self,
                      file_path: Path,
                      old_content: str,
                      new_content: str,
                      validate: bool = True) -> Dict[str, Any]:
        """Apply a patch to a file with validation."""
        # TODO: Implement safe patch application
        # - Validate the patch can be applied
        # - Create backup
        # - Apply changes
        # - Validate result
        
        return {
            "applied": False,
            "backup_path": None,
            "changes": {
                "lines_added": 0,
                "lines_removed": 0,
                "lines_modified": 0
            }
        }


class PRCreationTool(BaseTool):
    """Tool for creating pull requests."""
    
    def __init__(self):
        super().__init__("open_pr")
    
    async def _execute(self,
                      repo_url: str,
                      title: str,
                      body: str,
                      branch: str,
                      files: List[str]) -> Dict[str, Any]:
        """Create a pull request with the given changes."""
        # TODO: Implement GitHub PR creation
        # - Create branch
        # - Commit changes
        # - Push to remote
        # - Create PR via API
        
        return {
            "pr_url": f"https://github.com/example/repo/pull/123",
            "pr_number": 123,
            "branch": branch
        }