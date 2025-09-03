"""Enhanced multi-language test runner tool."""
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseTool
from ..evaluation.models import ExecutionStatus, TestExecution
from .language_support import MultiLanguageTestRunner, LanguageDetector, Language, TestFramework


class TestRunnerTool(BaseTool):
    """Enhanced tool for executing test suites across multiple languages."""
    
    def __init__(self):
        super().__init__("run_tests")
        self.multi_runner = MultiLanguageTestRunner()
    
    async def _execute(self, 
                      repo_path: Path, 
                      test_command: Optional[str] = None,
                      timeout: int = 120) -> TestExecution:
        """Execute tests and return structured results with multi-language support."""
        
        # Analyze repository to determine language and framework
        repo_analysis = self.multi_runner.analyze_repository(repo_path)
        
        if "error" in repo_analysis:
            return TestExecution(
                result=ExecutionStatus.FAILED,
                stdout="",
                stderr=f"Repository analysis failed: {repo_analysis['error']}",
                duration=0.0,
                exit_code=1,
                tests_passed=0,
                tests_failed=0,
                error_message=repo_analysis["error"]
            )
        
        # Use provided test command or auto-detected one
        final_command = test_command or repo_analysis.get("test_command")
        
        if not final_command:
            return TestExecution(
                result=ExecutionStatus.FAILED,
                stdout="",
                stderr="No test command available",
                duration=0.0,
                exit_code=1,
                tests_passed=0,
                tests_failed=0,
                error_message="Could not determine test command"
            )
        
        # Execute the test command
        try:
            result = subprocess.run(
                final_command.split(),
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return TestExecution(
                result=ExecutionStatus.FAILED,
                stdout="",
                stderr=f"Test execution timed out after {timeout} seconds",
                duration=float(timeout),
                exit_code=124,  # Standard timeout exit code
                tests_passed=0,
                tests_failed=0,
                error_message=f"Timeout after {timeout} seconds"
            )
        except Exception as e:
            return TestExecution(
                result=ExecutionStatus.FAILED,
                stdout="",
                stderr=f"Test execution failed: {str(e)}",
                duration=0.0,
                exit_code=1,
                tests_passed=0,
                tests_failed=0,
                error_message=str(e)
            )
        
        # Parse results using language-specific handler
        language = Language(repo_analysis["language"])
        handler = self.multi_runner.get_handler(language)
        parsed_results = handler.parse_test_output(result.stdout, result.stderr, result.returncode)
        
        # Extract main error message
        error_message = None
        if result.returncode != 0:
            error_message = self._extract_main_error(result.stderr, result.stdout, parsed_results)
        
        test_result = ExecutionStatus.PASSED if result.returncode == 0 else ExecutionStatus.FAILED
        
        return TestExecution(
            result=test_result,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=parsed_results.get("duration", 0.0),
            exit_code=result.returncode,
            tests_passed=parsed_results.get("tests_passed", 0),
            tests_failed=parsed_results.get("tests_failed", 0),
            error_message=error_message
        )
    
    def _extract_main_error(self, stderr: str, stdout: str, parsed_results: Dict[str, Any]) -> Optional[str]:
        """Extract the main error message from test output."""
        
        # Check for errors in parsed results first
        if parsed_results.get("errors"):
            return parsed_results["errors"][0]  # Return first error
        
        # Check stderr
        if stderr.strip():
            lines = stderr.strip().split('\n')
            for line in lines:
                if any(keyword in line for keyword in ["Error:", "error:", "FAILED", "FAIL:"]):
                    return line.strip()
            return lines[0] if lines else None
        
        # Check stdout for error patterns
        if stdout.strip():
            lines = stdout.strip().split('\n')
            for line in lines:
                if any(keyword in line for keyword in ["Error:", "NameError:", "ImportError:", "TypeError:", "SyntaxError:"]):
                    return line.strip()
        
        return "Test execution failed"
    
    def analyze_repository(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository to get language and test configuration info."""
        return self.multi_runner.analyze_repository(repo_path)
    
    def detect_test_framework(self, repo_path: Path) -> str:
        """Detect the test framework used in the repository."""
        analysis = self.analyze_repository(repo_path)
        return analysis.get("framework", "unknown")
    
    def get_test_command(self, repo_path: Path, framework: str = None) -> str:
        """Get the appropriate test command for the framework."""
        analysis = self.analyze_repository(repo_path)
        return analysis.get("test_command", "echo 'No test command available'")


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