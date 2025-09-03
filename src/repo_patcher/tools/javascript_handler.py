"""JavaScript/TypeScript language handler for test fixing."""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from .language_support import BaseLanguageHandler, TestFramework, Language


class JavaScriptHandler(BaseLanguageHandler):
    """Handler for JavaScript and TypeScript projects."""
    
    def detect_framework(self, repo_path: Path) -> Optional[TestFramework]:
        """Detect the test framework used in the repository."""
        package_json_path = repo_path / "package.json"
        
        if not package_json_path.exists():
            return None
        
        try:
            with open(package_json_path) as f:
                package_data = json.load(f)
            
            # Check dependencies and devDependencies
            all_deps = {}
            if "dependencies" in package_data:
                all_deps.update(package_data["dependencies"])
            if "devDependencies" in package_data:
                all_deps.update(package_data["devDependencies"])
            
            # Prioritize by popularity and reliability
            if "jest" in all_deps:
                return TestFramework.JEST
            elif "vitest" in all_deps:
                return TestFramework.VITEST
            elif "mocha" in all_deps:
                return TestFramework.MOCHA
            
            # Check for Jest configuration
            if "jest" in package_data:
                return TestFramework.JEST
            
            # Check for specific config files
            if (repo_path / "jest.config.js").exists() or (repo_path / "jest.config.json").exists():
                return TestFramework.JEST
            if (repo_path / "vitest.config.js").exists() or (repo_path / "vite.config.js").exists():
                return TestFramework.VITEST
            if (repo_path / "mocha.opts").exists() or (repo_path / ".mocharc.json").exists():
                return TestFramework.MOCHA
            
            return None
            
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def get_test_command(self, repo_path: Path, framework: TestFramework) -> str:
        """Get the test command for the framework."""
        if framework == TestFramework.JEST:
            return "npm test"
        elif framework == TestFramework.VITEST:
            return "npm run test"
        elif framework == TestFramework.MOCHA:
            return "npm test"
        else:
            return "npm test"  # Default
    
    def parse_test_output(self, stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
        """Parse test framework output into structured format."""
        result = {
            "tests_passed": 0,
            "tests_failed": 0,
            "test_suites_passed": 0,
            "test_suites_failed": 0,
            "errors": [],
            "failures": [],
            "duration": 0.0
        }
        
        # Parse Jest output - check for Jest patterns
        if ("Jest" in stdout or "jest" in stdout or 
            "Test Suites:" in stdout or 
            "Tests:" in stdout and "total" in stdout):
            result.update(self._parse_jest_output(stdout, stderr))
        
        # Parse Vitest output
        elif "vitest" in stdout.lower() or "vite" in stdout.lower():
            result.update(self._parse_vitest_output(stdout, stderr))
        
        # Parse Mocha output
        elif "mocha" in stdout.lower():
            result.update(self._parse_mocha_output(stdout, stderr))
        
        # Generic parsing for unknown frameworks
        else:
            result.update(self._parse_generic_output(stdout, stderr))
        
        return result
    
    def _parse_jest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse Jest-specific output."""
        result = {}
        
        # Look for test summary
        # Example: "Tests:       1 failed, 2 passed, 3 total"
        test_summary = re.search(r'Tests:\s+(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+passed,?\s*)?(\d+)\s+total', stdout)
        if test_summary:
            failed = int(test_summary.group(1) or 0)
            passed = int(test_summary.group(2) or 0)
            result["tests_failed"] = failed
            result["tests_passed"] = passed
        
        # Look for test suite summary
        # Example: "Test Suites: 1 failed, 1 total"
        suite_summary = re.search(r'Test Suites:\s+(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+passed,?\s*)?(\d+)\s+total', stdout)
        if suite_summary:
            failed = int(suite_summary.group(1) or 0)
            passed = int(suite_summary.group(2) or 0)
            result["test_suites_failed"] = failed
            result["test_suites_passed"] = passed
        
        # Extract error messages
        errors = []
        # Look for error patterns
        error_patterns = [
            r'● (.+)\n\n\s+(.+)\n',  # Jest error format
            r'ReferenceError: (.+)',
            r'TypeError: (.+)',
            r'SyntaxError: (.+)',
            r'Error: (.+)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, stdout + stderr, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    errors.append(f"{match[0]}: {match[1]}")
                else:
                    errors.append(match)
        
        result["errors"] = errors[:5]  # Limit to first 5 errors
        
        # Extract duration
        duration_match = re.search(r'Time:\s+([\d.]+)\s*s', stdout)
        if duration_match:
            result["duration"] = float(duration_match.group(1))
        
        return result
    
    def _parse_vitest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse Vitest-specific output."""
        result = {}
        
        # Vitest output format: "✓ 2 passed (1ms)"
        passed_match = re.search(r'✓\s+(\d+)\s+passed', stdout)
        if passed_match:
            result["tests_passed"] = int(passed_match.group(1))
        
        # Failed tests: "❯ 1 failed"
        failed_match = re.search(r'❯\s+(\d+)\s+failed', stdout)
        if failed_match:
            result["tests_failed"] = int(failed_match.group(1))
        
        return result
    
    def _parse_mocha_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse Mocha-specific output."""
        result = {}
        
        # Mocha output: "  2 passing (10ms)" or "  1 failing"
        passed_match = re.search(r'(\d+)\s+passing', stdout)
        if passed_match:
            result["tests_passed"] = int(passed_match.group(1))
        
        failed_match = re.search(r'(\d+)\s+failing', stdout)
        if failed_match:
            result["tests_failed"] = int(failed_match.group(1))
        
        return result
    
    def _parse_generic_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse generic test output."""
        # Try to find common patterns
        result = {}
        
        # Look for pass/fail counts
        passed_patterns = [r'(\d+)\s+(?:test|spec)s?\s+passed', r'✓\s*(\d+)']
        failed_patterns = [r'(\d+)\s+(?:test|spec)s?\s+failed', r'✗\s*(\d+)']
        
        for pattern in passed_patterns:
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                result["tests_passed"] = int(match.group(1))
                break
        
        for pattern in failed_patterns:
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                result["tests_failed"] = int(match.group(1))
                break
        
        return result
    
    def get_dependency_info(self, repo_path: Path) -> Dict[str, Any]:
        """Get dependency information from package.json."""
        package_json_path = repo_path / "package.json"
        
        if not package_json_path.exists():
            return {"error": "No package.json found"}
        
        try:
            with open(package_json_path) as f:
                package_data = json.load(f)
            
            dependencies = package_data.get("dependencies", {})
            dev_dependencies = package_data.get("devDependencies", {})
            
            return {
                "package_manager": self._detect_package_manager(repo_path),
                "dependencies": dependencies,
                "devDependencies": dev_dependencies,
                "scripts": package_data.get("scripts", {}),
                "node_version": package_data.get("engines", {}).get("node", "unknown")
            }
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": f"Could not parse package.json: {str(e)}"}
    
    def _detect_package_manager(self, repo_path: Path) -> str:
        """Detect the package manager being used."""
        if (repo_path / "yarn.lock").exists():
            return "yarn"
        elif (repo_path / "pnpm-lock.yaml").exists():
            return "pnpm"
        elif (repo_path / "package-lock.json").exists():
            return "npm"
        else:
            return "npm"  # Default
    
    def suggest_imports(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Suggest import statements based on error messages."""
        suggestions = []
        
        # Common JavaScript/TypeScript error patterns
        if "is not defined" in error_message or "ReferenceError" in error_message:
            # Extract the undefined identifier
            match = re.search(r"'?(\w+)'?\s+is not defined", error_message)
            if match:
                identifier = match.group(1)
                suggestions.extend(self._suggest_for_identifier(identifier, context))
        
        elif "Cannot find module" in error_message:
            # Extract module name
            match = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", error_message)
            if match:
                module_name = match.group(1)
                suggestions.append(f"npm install {module_name}")
                
                # Suggest import statement
                if module_name.startswith("./") or module_name.startswith("../"):
                    # Relative import
                    suggestions.append(f"import {{ /* exports */ }} from '{module_name}';")
                else:
                    # Package import
                    suggestions.append(f"import {module_name.replace('-', '')} from '{module_name}';")
        
        elif "Property" in error_message and "does not exist" in error_message:
            # TypeScript type errors
            match = re.search(r"Property '(\w+)' does not exist on type", error_message)
            if match:
                prop = match.group(1)
                suggestions.append(f"// Consider adding '{prop}' to the type definition")
                suggestions.append(f"// Or use type assertion: (obj as any).{prop}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _suggest_for_identifier(self, identifier: str, context: Dict[str, Any]) -> List[str]:
        """Suggest imports for a specific identifier."""
        suggestions = []
        
        # Check common imports from config
        if identifier in self.config.common_imports:
            suggestions.append(self.config.common_imports[identifier])
        
        # Common Node.js modules
        common_node_modules = {
            "fs": "import fs from 'fs';",
            "path": "import path from 'path';",
            "util": "import util from 'util';",
            "crypto": "import crypto from 'crypto';",
            "Buffer": "import { Buffer } from 'buffer';",
            "process": "// process is a global object in Node.js",
            "console": "// console is available globally",
            "setTimeout": "// setTimeout is available globally",
            "setInterval": "// setInterval is available globally"
        }
        
        if identifier in common_node_modules:
            suggestions.append(common_node_modules[identifier])
        
        # Check if it might be a React component
        if identifier[0].isupper():
            suggestions.append(f"import {identifier} from './{identifier}';")
            suggestions.append(f"import {{ {identifier} }} from './components';")
        
        # Check if it might be a utility function
        else:
            suggestions.append(f"import {{ {identifier} }} from './utils';")
            suggestions.append(f"import {{ {identifier} }} from './helpers';")
        
        return suggestions