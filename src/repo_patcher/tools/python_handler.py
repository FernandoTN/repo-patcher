"""Python language handler for test fixing."""
import re
import ast
import configparser
from pathlib import Path
from typing import Dict, List, Optional, Any

from .language_support import BaseLanguageHandler, TestFramework


class PythonHandler(BaseLanguageHandler):
    """Handler for Python projects."""
    
    def detect_framework(self, repo_path: Path) -> Optional[TestFramework]:
        """Detect the test framework used in the repository."""
        
        # Check for pytest first (most common)
        if self._has_pytest_config(repo_path):
            return TestFramework.PYTEST
        
        # Check for pytest in requirements
        if self._has_pytest_in_requirements(repo_path):
            return TestFramework.PYTEST
        
        # Check for test files with pytest patterns
        if self._has_pytest_test_files(repo_path):
            return TestFramework.PYTEST
        
        # Default to pytest for Python projects
        return TestFramework.PYTEST
    
    def _has_pytest_config(self, repo_path: Path) -> bool:
        """Check for pytest configuration files."""
        config_files = [
            "pytest.ini",
            "pyproject.toml",
            "setup.cfg",
            "tox.ini"
        ]
        
        for config_file in config_files:
            config_path = repo_path / config_file
            if config_path.exists():
                if config_file == "pyproject.toml":
                    # Check if pytest is configured in pyproject.toml
                    try:
                        import toml
                        with open(config_path) as f:
                            data = toml.load(f)
                        if "tool" in data and "pytest" in data["tool"]:
                            return True
                    except ImportError:
                        # toml not available, assume pytest if pyproject.toml exists
                        return True
                else:
                    return True
        
        return False
    
    def _has_pytest_in_requirements(self, repo_path: Path) -> bool:
        """Check if pytest is listed in requirements files."""
        req_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "dev-requirements.txt",
            "test-requirements.txt"
        ]
        
        for req_file in req_files:
            req_path = repo_path / req_file
            if req_path.exists():
                try:
                    with open(req_path) as f:
                        content = f.read().lower()
                        if "pytest" in content:
                            return True
                except FileNotFoundError:
                    continue
        
        return False
    
    def _has_pytest_test_files(self, repo_path: Path) -> bool:
        """Check for pytest-style test files."""
        # Look for test files with pytest patterns
        test_files = list(repo_path.rglob("test_*.py")) + list(repo_path.rglob("*_test.py"))
        
        if not test_files:
            return False
        
        # Check if any test file uses pytest patterns
        for test_file in test_files[:5]:  # Check first 5 files
            try:
                with open(test_file) as f:
                    content = f.read()
                    if "def test_" in content or "import pytest" in content:
                        return True
            except (FileNotFoundError, UnicodeDecodeError):
                continue
        
        return False
    
    def get_test_command(self, repo_path: Path, framework: TestFramework) -> str:
        """Get the test command for the framework."""
        if framework == TestFramework.PYTEST:
            # Check for common test directories
            if (repo_path / "tests").exists():
                return "python -m pytest tests/ -v"
            elif (repo_path / "test").exists():
                return "python -m pytest test/ -v"
            else:
                return "python -m pytest -v"
        else:
            return "python -m pytest -v"  # Default
    
    def parse_test_output(self, stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
        """Parse test framework output into structured format."""
        result = {
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "failures": [],
            "duration": 0.0
        }
        
        # Parse pytest output
        result.update(self._parse_pytest_output(stdout, stderr))
        
        return result
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse pytest-specific output."""
        result = {}
        
        # Look for test summary
        # Example: "1 failed, 3 passed in 0.02s"
        summary_patterns = [
            r'(\d+)\s+failed,?\s*(\d+)\s+passed\s+in',
            r'(\d+)\s+passed\s+in',
            r'(\d+)\s+failed\s+in'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, stdout)
            if match:
                if len(match.groups()) == 2:
                    result["tests_failed"] = int(match.group(1))
                    result["tests_passed"] = int(match.group(2))
                elif "passed" in match.group(0):
                    result["tests_passed"] = int(match.group(1))
                elif "failed" in match.group(0):
                    result["tests_failed"] = int(match.group(1))
                break
        
        # Extract error messages
        errors = []
        
        # Look for common Python errors
        error_patterns = [
            r'E\s+(\w+Error: .+)',
            r'FAILED .+ - (\w+Error: .+)',
            r'ERROR .+ - (\w+Error: .+)',
            r'(\w+Error: .+)',
            r'AssertionError: (.+)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, stdout + stderr, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    errors.extend([m for m in match if m.strip()])
                else:
                    errors.append(match)
        
        result["errors"] = list(set(errors))[:5]  # Remove duplicates, limit to 5
        
        # Extract duration
        duration_match = re.search(r'in ([\d.]+)s', stdout)
        if duration_match:
            result["duration"] = float(duration_match.group(1))
        
        return result
    
    def get_dependency_info(self, repo_path: Path) -> Dict[str, Any]:
        """Get dependency information from Python package files."""
        info = {
            "python_version": "unknown",
            "requirements": [],
            "dev_requirements": [],
            "package_manager": "pip"
        }
        
        # Check pyproject.toml
        pyproject_path = repo_path / "pyproject.toml"
        if pyproject_path.exists():
            info.update(self._parse_pyproject_toml(pyproject_path))
        
        # Check requirements.txt
        req_path = repo_path / "requirements.txt"
        if req_path.exists():
            info["requirements"] = self._parse_requirements(req_path)
        
        # Check setup.py
        setup_path = repo_path / "setup.py"
        if setup_path.exists():
            info.update(self._parse_setup_py(setup_path))
        
        return info
    
    def _parse_pyproject_toml(self, pyproject_path: Path) -> Dict[str, Any]:
        """Parse pyproject.toml for dependency information."""
        try:
            import toml
            with open(pyproject_path) as f:
                data = toml.load(f)
            
            result = {}
            
            # Get Python version requirement
            if "tool" in data and "poetry" in data["tool"]:
                # Poetry project
                poetry_data = data["tool"]["poetry"]
                if "dependencies" in poetry_data and "python" in poetry_data["dependencies"]:
                    result["python_version"] = poetry_data["dependencies"]["python"]
                
                result["dependencies"] = poetry_data.get("dependencies", {})
                result["dev_dependencies"] = poetry_data.get("dev-dependencies", {})
                result["package_manager"] = "poetry"
            
            elif "project" in data:
                # PEP 621 project
                project_data = data["project"]
                if "requires-python" in project_data:
                    result["python_version"] = project_data["requires-python"]
                
                result["dependencies"] = project_data.get("dependencies", [])
                result["package_manager"] = "pip"
            
            return result
            
        except (ImportError, Exception):
            # toml not available or parsing failed
            return {"package_manager": "pip"}
    
    def _parse_requirements(self, req_path: Path) -> List[str]:
        """Parse requirements.txt file."""
        try:
            with open(req_path) as f:
                lines = f.readlines()
            
            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    requirements.append(line)
            
            return requirements
            
        except FileNotFoundError:
            return []
    
    def _parse_setup_py(self, setup_path: Path) -> Dict[str, Any]:
        """Parse setup.py for basic information."""
        try:
            with open(setup_path) as f:
                content = f.read()
            
            result = {}
            
            # Try to extract python_requires
            python_req_match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
            if python_req_match:
                result["python_version"] = python_req_match.group(1)
            
            return result
            
        except FileNotFoundError:
            return {}
    
    def suggest_imports(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Suggest import statements based on error messages."""
        suggestions = []
        
        # Common Python error patterns
        if "NameError: name" in error_message:
            # Extract the undefined name
            match = re.search(r"NameError: name '(\w+)' is not defined", error_message)
            if match:
                name = match.group(1)
                suggestions.extend(self._suggest_for_name(name, context))
        
        elif "ModuleNotFoundError: No module named" in error_message:
            # Extract module name
            match = re.search(r"No module named '([^']+)'", error_message)
            if match:
                module_name = match.group(1)
                suggestions.append(f"pip install {module_name}")
                suggestions.append(f"import {module_name}")
        
        elif "ImportError" in error_message:
            # Handle various import errors
            if "cannot import name" in error_message:
                match = re.search(r"cannot import name '(\w+)' from '([^']+)'", error_message)
                if match:
                    name, module = match.groups()
                    suggestions.append(f"# Check if '{name}' exists in module '{module}'")
                    suggestions.append(f"from {module} import {name}")
        
        elif "AttributeError" in error_message:
            # Handle attribute errors that might be import-related
            match = re.search(r"module '(\w+)' has no attribute '(\w+)'", error_message)
            if match:
                module, attr = match.groups()
                suggestions.append(f"from {module} import {attr}")
                suggestions.append(f"# Check if '{attr}' is available in {module}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _suggest_for_name(self, name: str, context: Dict[str, Any]) -> List[str]:
        """Suggest imports for a specific name."""
        suggestions = []
        
        # Check common imports from config
        if name in self.config.common_imports:
            suggestions.append(self.config.common_imports[name])
        
        # Common Python standard library
        stdlib_suggestions = {
            "datetime": "from datetime import datetime",
            "date": "from datetime import date",
            "time": "import time",
            "random": "import random",
            "math": "import math",
            "os": "import os",
            "sys": "import sys",
            "json": "import json",
            "re": "import re",
            "collections": "import collections",
            "itertools": "import itertools",
            "functools": "import functools",
            "pathlib": "from pathlib import Path",
            "typing": "from typing import List, Dict, Optional"
        }
        
        if name.lower() in stdlib_suggestions:
            suggestions.append(stdlib_suggestions[name.lower()])
        
        # Check if it might be a class (PascalCase)
        if name[0].isupper() and name.isalpha():
            suggestions.append(f"from .models import {name}")
            suggestions.append(f"from .{name.lower()} import {name}")
        
        # Check if it might be a function (snake_case)
        elif "_" in name or name.islower():
            suggestions.append(f"from .utils import {name}")
            suggestions.append(f"from .helpers import {name}")
        
        return suggestions