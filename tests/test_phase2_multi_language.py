"""Comprehensive tests for Phase 2 multi-language support."""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.repo_patcher.tools.language_support import (
    Language, TestFramework, LanguageDetector, MultiLanguageTestRunner,
    PYTHON_CONFIG, JAVASCRIPT_CONFIG, TYPESCRIPT_CONFIG, GO_CONFIG
)
from src.repo_patcher.tools.python_handler import PythonHandler
from src.repo_patcher.tools.javascript_handler import JavaScriptHandler
from src.repo_patcher.tools.go_handler import GoHandler
from src.repo_patcher.tools.test_runner import TestRunnerTool


class TestLanguageDetection:
    """Test language detection functionality."""
    
    def test_detect_python_project(self):
        """Test detecting Python projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Python project files
            (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
            (repo_path / "src" / "main.py").parent.mkdir(exist_ok=True)
            (repo_path / "src" / "main.py").write_text("def main(): pass")
            (repo_path / "tests" / "test_main.py").parent.mkdir(exist_ok=True)
            (repo_path / "tests" / "test_main.py").write_text("def test_main(): pass")
            
            language = LanguageDetector.detect_language(repo_path)
            assert language == Language.PYTHON
    
    def test_detect_javascript_project(self):
        """Test detecting JavaScript projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create JavaScript project files
            package_json = {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {"lodash": "^4.17.21"}
            }
            (repo_path / "package.json").write_text(json.dumps(package_json))
            (repo_path / "src" / "index.js").parent.mkdir(exist_ok=True)
            (repo_path / "src" / "index.js").write_text("console.log('Hello World');")
            
            language = LanguageDetector.detect_language(repo_path)
            assert language == Language.JAVASCRIPT
    
    def test_detect_typescript_project(self):
        """Test detecting TypeScript projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create TypeScript project files
            (repo_path / "package.json").write_text('{"name": "test", "devDependencies": {"typescript": "^4.0.0"}}')
            (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "es2020"}}')
            (repo_path / "src" / "index.ts").parent.mkdir(exist_ok=True)
            (repo_path / "src" / "index.ts").write_text("const message: string = 'Hello';")
            
            language = LanguageDetector.detect_language(repo_path)
            assert language == Language.TYPESCRIPT
    
    def test_detect_go_project(self):
        """Test detecting Go projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Go project files
            (repo_path / "go.mod").write_text("module test-project\n\ngo 1.19")
            (repo_path / "main.go").write_text("package main\n\nfunc main() {}")
            (repo_path / "main_test.go").write_text("package main\n\nimport \"testing\"")
            
            language = LanguageDetector.detect_language(repo_path)
            assert language == Language.GO
    
    def test_detect_unknown_project(self):
        """Test handling unknown project types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create empty directory
            language = LanguageDetector.detect_language(repo_path)
            assert language is None


class TestPythonHandler:
    """Test Python language handler."""
    
    def test_detect_pytest_framework(self):
        """Test pytest framework detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create pytest configuration
            (repo_path / "pytest.ini").write_text("[tool:pytest]\npython_files = test_*.py")
            
            handler = PythonHandler(PYTHON_CONFIG)
            framework = handler.detect_framework(repo_path)
            assert framework == TestFramework.PYTEST
    
    def test_parse_pytest_output(self):
        """Test parsing pytest output."""
        handler = PythonHandler(PYTHON_CONFIG)
        
        stdout = """
        ========================= test session starts =========================
        collected 3 items

        tests/test_calculator.py::test_add PASSED                      [ 33%]
        tests/test_calculator.py::test_subtract FAILED                 [ 66%]
        tests/test_calculator.py::test_multiply PASSED                 [100%]

        ============================== FAILURES ==============================
        _________________________ test_subtract ____________________________

            def test_subtract():
        >       assert subtract(5, 3) == 2
        E       NameError: name 'subtract' is not defined

        tests/test_calculator.py:10: NameError
        ==================== 1 failed, 2 passed in 0.05s ====================
        """
        
        result = handler.parse_test_output(stdout, "", 1)
        assert result["tests_passed"] == 2
        assert result["tests_failed"] == 1
        assert result["duration"] == 0.05
        assert len(result["errors"]) > 0
        assert "NameError" in result["errors"][0]
    
    def test_suggest_imports_for_nameerror(self):
        """Test import suggestions for NameError."""
        handler = PythonHandler(PYTHON_CONFIG)
        
        error_message = "NameError: name 'sqrt' is not defined"
        suggestions = handler.suggest_imports(error_message, {})
        
        assert len(suggestions) > 0
        assert any("math" in suggestion for suggestion in suggestions)
    
    def test_get_dependency_info(self):
        """Test getting Python dependency information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create requirements.txt
            (repo_path / "requirements.txt").write_text("requests>=2.25.0\nnumpy==1.21.0")
            
            handler = PythonHandler(PYTHON_CONFIG)
            info = handler.get_dependency_info(repo_path)
            
            assert "requirements" in info
            assert len(info["requirements"]) == 2
            assert "requests>=2.25.0" in info["requirements"]


class TestJavaScriptHandler:
    """Test JavaScript language handler."""
    
    def test_detect_jest_framework(self):
        """Test Jest framework detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create package.json with Jest
            package_json = {
                "name": "test-project",
                "devDependencies": {"jest": "^29.0.0"}
            }
            (repo_path / "package.json").write_text(json.dumps(package_json))
            
            handler = JavaScriptHandler(JAVASCRIPT_CONFIG)
            framework = handler.detect_framework(repo_path)
            assert framework == TestFramework.JEST
    
    def test_parse_jest_output(self):
        """Test parsing Jest output."""
        handler = JavaScriptHandler(JAVASCRIPT_CONFIG)
        
        stdout = """
        PASS  src/utils.test.js
          Utils
            ✓ should process data correctly (2 ms)
            ✕ should handle empty array (1 ms)

        ● Utils › should handle empty array

          ReferenceError: _ is not defined

            4 |   function getUniqueValues(array) {
          > 5 |       return _.uniq(array);
              |              ^
            6 |   }

        Test Suites: 1 failed, 0 passed, 1 total
        Tests:       1 failed, 1 passed, 2 total
        Snapshots:   0 total
        Time:        0.5 s
        """
        
        result = handler.parse_test_output(stdout, "", 1)
        assert result["tests_passed"] == 1
        assert result["tests_failed"] == 1
        assert result["test_suites_failed"] == 1
        assert result["duration"] == 0.5
        assert len(result["errors"]) > 0
    
    def test_suggest_imports_for_reference_error(self):
        """Test import suggestions for ReferenceError."""
        handler = JavaScriptHandler(JAVASCRIPT_CONFIG)
        
        error_message = "ReferenceError: _ is not defined"
        suggestions = handler.suggest_imports(error_message, {})
        
        assert len(suggestions) > 0
        # Should suggest importing lodash or utility functions
    
    def test_get_dependency_info(self):
        """Test getting JavaScript dependency information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create package.json
            package_json = {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {"lodash": "^4.17.21"},
                "devDependencies": {"jest": "^29.0.0"},
                "scripts": {"test": "jest"}
            }
            (repo_path / "package.json").write_text(json.dumps(package_json))
            (repo_path / "package-lock.json").write_text("{}")  # NPM lock file
            
            handler = JavaScriptHandler(JAVASCRIPT_CONFIG)
            info = handler.get_dependency_info(repo_path)
            
            assert info["package_manager"] == "npm"
            assert info["dependencies"]["lodash"] == "^4.17.21"
            assert info["devDependencies"]["jest"] == "^29.0.0"


class TestGoHandler:
    """Test Go language handler."""
    
    def test_detect_go_test_framework(self):
        """Test go test framework detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create go.mod
            (repo_path / "go.mod").write_text("module test-project\n\ngo 1.19")
            
            handler = GoHandler(GO_CONFIG)
            framework = handler.detect_framework(repo_path)
            assert framework == TestFramework.GO_TEST
    
    def test_parse_go_test_output(self):
        """Test parsing go test output."""
        handler = GoHandler(GO_CONFIG)
        
        stdout = """
        === RUN   TestFormatMessage
        --- PASS: TestFormatMessage (0.00s)
        === RUN   TestGetGreeting  
        --- FAIL: TestGetGreeting (0.00s)
            utils_test.go:15: Expected "Hello Bob", got "Hello"
        FAIL
        exit status 1
        FAIL    test-project    0.002s
        """
        
        stderr = """
        # test-project
        ./utils.go:6:12: undefined: fmt
        """
        
        result = handler.parse_go_test_output(stdout, stderr)
        assert result["tests_passed"] == 1
        assert result["tests_failed"] == 1
        assert len(result["build_errors"]) > 0
        assert "undefined: fmt" in str(result["build_errors"])
    
    def test_suggest_imports_for_undefined(self):
        """Test import suggestions for undefined identifiers."""
        handler = GoHandler(GO_CONFIG)
        
        error_message = "undefined: fmt"
        suggestions = handler.suggest_imports(error_message, {})
        
        assert len(suggestions) > 0
        assert any('import "fmt"' in suggestion for suggestion in suggestions)
    
    def test_get_dependency_info(self):
        """Test getting Go dependency information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create go.mod
            go_mod_content = """module test-project

go 1.19

require (
    github.com/gorilla/mux v1.8.0
    github.com/stretchr/testify v1.8.0
)
"""
            (repo_path / "go.mod").write_text(go_mod_content)
            
            handler = GoHandler(GO_CONFIG)
            info = handler.get_dependency_info(repo_path)
            
            assert info["module"] == "test-project"
            assert info["go_version"] == "1.19"
            assert len(info["dependencies"]) == 2
            assert any("gorilla/mux" in dep for dep in info["dependencies"])


class TestMultiLanguageTestRunner:
    """Test the multi-language test runner."""
    
    def test_analyze_python_repository(self):
        """Test analyzing a Python repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Python project
            (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
            (repo_path / "src" / "main.py").parent.mkdir(exist_ok=True)
            (repo_path / "src" / "main.py").write_text("def main(): pass")
            
            runner = MultiLanguageTestRunner()
            analysis = runner.analyze_repository(repo_path)
            
            assert analysis["language"] == "python"
            assert analysis["framework"] == "pytest"
            assert "python -m pytest" in analysis["test_command"]
    
    def test_analyze_javascript_repository(self):
        """Test analyzing a JavaScript repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create JavaScript project
            package_json = {
                "name": "test-project",
                "devDependencies": {"jest": "^29.0.0"},
                "scripts": {"test": "jest"}
            }
            (repo_path / "package.json").write_text(json.dumps(package_json))
            (repo_path / "src" / "index.js").parent.mkdir(exist_ok=True)
            (repo_path / "src" / "index.js").write_text("console.log('test');")
            
            runner = MultiLanguageTestRunner()
            analysis = runner.analyze_repository(repo_path)
            
            assert analysis["language"] == "javascript"
            assert analysis["framework"] == "jest"
            assert analysis["test_command"] == "npm test"
    
    def test_analyze_go_repository(self):
        """Test analyzing a Go repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Go project
            (repo_path / "go.mod").write_text("module test-project\n\ngo 1.19")
            (repo_path / "main.go").write_text("package main\n\nfunc main() {}")
            
            runner = MultiLanguageTestRunner()
            analysis = runner.analyze_repository(repo_path)
            
            assert analysis["language"] == "go"
            assert analysis["framework"] == "go_test"
            assert analysis["test_command"] == "go test ./... -v"
    
    def test_analyze_unknown_repository(self):
        """Test handling unknown repository types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create empty repository
            runner = MultiLanguageTestRunner()
            analysis = runner.analyze_repository(repo_path)
            
            assert "error" in analysis
            assert "Could not detect programming language" in analysis["error"]


class TestEnhancedTestRunner:
    """Test the enhanced test runner with multi-language support."""
    
    @patch('subprocess.run')
    def test_execute_python_tests(self, mock_run):
        """Test executing Python tests."""
        # Mock subprocess result
        mock_run.return_value = Mock(
            returncode=1,
            stdout="1 failed, 2 passed in 0.05s",
            stderr="NameError: name 'sqrt' is not defined"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Python project
            (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
            (repo_path / "tests" / "test_main.py").parent.mkdir(exist_ok=True)
            (repo_path / "tests" / "test_main.py").write_text("def test_main(): pass")
            
            runner = TestRunnerTool()
            result = await runner._execute(repo_path)
            
            assert result.result.value == "failed"
            assert result.tests_passed == 2
            assert result.tests_failed == 1
            assert "NameError" in result.error_message
    
    @patch('subprocess.run')
    def test_execute_javascript_tests(self, mock_run):
        """Test executing JavaScript tests."""
        # Mock subprocess result
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Tests: 1 failed, 1 passed, 2 total\nTest Suites: 1 failed, 1 total\nTime: 0.5s",
            stderr=""
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create JavaScript project
            package_json = {"name": "test", "devDependencies": {"jest": "^29.0.0"}}
            (repo_path / "package.json").write_text(json.dumps(package_json))
            
            runner = TestRunnerTool()
            result = await runner._execute(repo_path)
            
            assert result.result.value == "failed"
            # JavaScript handler should parse the results correctly
    
    def test_analyze_repository_method(self):
        """Test the repository analysis method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create Python project
            (repo_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
            
            runner = TestRunnerTool()
            analysis = runner.analyze_repository(repo_path)
            
            assert analysis["language"] == "python"
            assert analysis["framework"] == "pytest"
            assert "python -m pytest" in analysis["test_command"]


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for multi-language support."""
    
    async def test_end_to_end_python_scenario(self):
        """Test complete Python scenario processing."""
        # This would test the E001 scenario we already have
        scenario_path = Path(__file__).parent.parent / "scenarios" / "E001_missing_import"
        
        if scenario_path.exists():
            runner = TestRunnerTool()
            repo_path = scenario_path / "repo"
            
            # Analyze repository
            analysis = runner.analyze_repository(repo_path)
            assert analysis["language"] == "python"
            assert analysis["framework"] == "pytest"
            
            # The actual test execution would require pytest to be available
            # and the scenario to be properly set up
    
    async def test_end_to_end_javascript_scenario(self):
        """Test complete JavaScript scenario processing."""
        scenario_path = Path(__file__).parent.parent / "scenarios" / "E002_js_missing_import"
        
        if scenario_path.exists():
            runner = TestRunnerTool()
            repo_path = scenario_path / "repo"
            
            # Analyze repository
            analysis = runner.analyze_repository(repo_path)
            assert analysis["language"] == "javascript"
            assert analysis["framework"] == "jest"
            
            # The actual test execution would require npm/jest to be available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])