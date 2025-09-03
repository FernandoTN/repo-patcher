"""Go language handler for test fixing."""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from .language_support import BaseLanguageHandler, TestFramework


class GoHandler(BaseLanguageHandler):
    """Handler for Go projects."""
    
    def detect_framework(self, repo_path: Path) -> Optional[TestFramework]:
        """Detect the test framework used in the repository."""
        
        # Check for go.mod (Go modules)
        if (repo_path / "go.mod").exists():
            return TestFramework.GO_TEST
        
        # Check for test files
        test_files = list(repo_path.rglob("*_test.go"))
        if test_files:
            return TestFramework.GO_TEST
        
        return None
    
    def get_test_command(self, repo_path: Path, framework: TestFramework) -> str:
        """Get the test command for the framework."""
        if framework == TestFramework.GO_TEST:
            return "go test ./... -v"
        else:
            return "go test ./... -v"  # Default
    
    def parse_test_output(self, stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
        """Parse test framework output into structured format."""
        result = {
            "tests_passed": 0,
            "tests_failed": 0,
            "build_errors": [],
            "test_errors": [],
            "duration": 0.0
        }
        
        result.update(self._parse_go_test_output(stdout, stderr))
        
        return result
    
    def _parse_go_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse go test output."""
        result = {}
        
        # Parse test results
        # Example output:
        # --- PASS: TestAdd (0.00s)
        # --- FAIL: TestSubtract (0.00s)
        # PASS
        # FAIL
        
        passed_tests = len(re.findall(r'^--- PASS:', stdout, re.MULTILINE))
        failed_tests = len(re.findall(r'^--- FAIL:', stdout, re.MULTILINE))
        
        result["tests_passed"] = passed_tests
        result["tests_failed"] = failed_tests
        
        # Extract build errors
        build_errors = []
        error_patterns = [
            r'# (.+)\n([^#]+?)(?=\n#|\n\n|\nPASS|\nFAIL|$)',  # Build errors
            r'(.+\.go:\d+:\d+: .+)',  # Compilation errors
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, stderr, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    build_errors.append(f"{match[0]}: {match[1].strip()}")
                else:
                    build_errors.append(match.strip())
        
        result["build_errors"] = build_errors[:5]  # Limit to 5 errors
        
        # Extract test errors from stdout
        test_errors = []
        # Look for test failure details
        failure_blocks = re.findall(r'--- FAIL: (\w+) \([^)]+\)\n((?:\s+.+\n)+)', stdout)
        for test_name, error_block in failure_blocks:
            test_errors.append(f"{test_name}: {error_block.strip()}")
        
        result["test_errors"] = test_errors[:5]  # Limit to 5 errors
        
        # Extract duration
        duration_match = re.search(r'ok\s+\S+\s+([\d.]+)s', stdout)
        if duration_match:
            result["duration"] = float(duration_match.group(1))
        
        return result
    
    def get_dependency_info(self, repo_path: Path) -> Dict[str, Any]:
        """Get dependency information from go.mod."""
        go_mod_path = repo_path / "go.mod"
        
        if not go_mod_path.exists():
            return {"error": "No go.mod found"}
        
        try:
            with open(go_mod_path) as f:
                content = f.read()
            
            result = {
                "module": "",
                "go_version": "",
                "dependencies": [],
                "package_manager": "go modules"
            }
            
            # Parse module name
            module_match = re.search(r'^module\s+(\S+)', content, re.MULTILINE)
            if module_match:
                result["module"] = module_match.group(1)
            
            # Parse Go version
            go_match = re.search(r'^go\s+([\d.]+)', content, re.MULTILINE)
            if go_match:
                result["go_version"] = go_match.group(1)
            
            # Parse dependencies
            require_block = re.search(r'require\s*\((.*?)\)', content, re.DOTALL)
            if require_block:
                dep_lines = require_block.group(1).strip().split('\n')
                dependencies = []
                for line in dep_lines:
                    line = line.strip()
                    if line and not line.startswith('//'):
                        # Remove any comments
                        line = re.sub(r'\s*//.*$', '', line)
                        dependencies.append(line)
                result["dependencies"] = dependencies
            else:
                # Single line require
                require_matches = re.findall(r'^require\s+(\S+\s+\S+)', content, re.MULTILINE)
                result["dependencies"] = require_matches
            
            return result
            
        except FileNotFoundError:
            return {"error": "Could not read go.mod"}
    
    def suggest_imports(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Suggest import statements based on error messages."""
        suggestions = []
        
        # Common Go error patterns
        if "undefined:" in error_message:
            # Extract the undefined identifier
            match = re.search(r'undefined: (\w+)', error_message)
            if match:
                identifier = match.group(1)
                suggestions.extend(self._suggest_for_identifier(identifier, context))
        
        elif "cannot find package" in error_message:
            # Extract package path
            match = re.search(r'cannot find package "([^"]+)"', error_message)
            if match:
                package_path = match.group(1)
                suggestions.append(f"go get {package_path}")
                suggestions.append(f'import "{package_path}"')
        
        elif "imported and not used" in error_message:
            # Unused import
            match = re.search(r'"([^"]+)" imported and not used', error_message)
            if match:
                package = match.group(1)
                suggestions.append(f'// Remove unused import: import "{package}"')
                suggestions.append(f'// Or use blank import: import _ "{package}"')
        
        elif "no such file or directory" in error_message:
            # Missing file/package
            suggestions.append("go mod tidy  # Update dependencies")
            suggestions.append("go get -u    # Update all dependencies")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _suggest_for_identifier(self, identifier: str, context: Dict[str, Any]) -> List[str]:
        """Suggest imports for a specific identifier."""
        suggestions = []
        
        # Check common imports from config
        if identifier in self.config.common_imports:
            suggestions.append(self.config.common_imports[identifier])
        
        # Common Go standard library packages
        stdlib_suggestions = {
            "fmt": 'import "fmt"',
            "log": 'import "log"',
            "os": 'import "os"',
            "io": 'import "io"',
            "http": 'import "net/http"',
            "json": 'import "encoding/json"',
            "time": 'import "time"',
            "errors": 'import "errors"',
            "context": 'import "context"',
            "sync": 'import "sync"',
            "strings": 'import "strings"',
            "strconv": 'import "strconv"',
            "bytes": 'import "bytes"',
            "bufio": 'import "bufio"',
            "regexp": 'import "regexp"',
            "math": 'import "math"',
            "sort": 'import "sort"'
        }
        
        # Check for common functions/types that come from stdlib
        stdlib_functions = {
            "Printf": 'import "fmt"',
            "Println": 'import "fmt"',
            "Sprintf": 'import "fmt"',
            "Marshal": 'import "encoding/json"',
            "Unmarshal": 'import "encoding/json"',
            "Sleep": 'import "time"',
            "Now": 'import "time"',
            "NewReader": 'import "strings" // or "bytes"',
            "NewRequest": 'import "net/http"',
            "Get": 'import "net/http"',
            "Post": 'import "net/http"',
            "Atoi": 'import "strconv"',
            "Itoa": 'import "strconv"'
        }
        
        if identifier in stdlib_suggestions:
            suggestions.append(stdlib_suggestions[identifier])
        elif identifier in stdlib_functions:
            suggestions.append(stdlib_functions[identifier])
        
        # Check if it might be from a third-party package
        # Common patterns for Go packages
        if identifier.startswith("Test"):
            suggestions.append('import "testing"')
        
        # If identifier looks like a struct/interface (starts with uppercase)
        if identifier[0].isupper():
            # Get module info from context
            module_info = context.get("dependencies", {})
            if isinstance(module_info, dict) and "module" in module_info:
                module_name = module_info["module"]
                suggestions.append(f'import "{module_name}/internal/{identifier.lower()}"')
                suggestions.append(f'import "{module_name}/pkg/{identifier.lower()}"')
        
        return suggestions
    
    def analyze_go_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Go file for structure and dependencies."""
        try:
            with open(file_path) as f:
                content = f.read()
            
            result = {
                "package": "",
                "imports": [],
                "functions": [],
                "types": [],
                "interfaces": []
            }
            
            # Extract package name
            package_match = re.search(r'^package\s+(\w+)', content, re.MULTILINE)
            if package_match:
                result["package"] = package_match.group(1)
            
            # Extract imports
            import_block = re.search(r'import\s*\((.*?)\)', content, re.DOTALL)
            if import_block:
                import_lines = import_block.group(1).strip().split('\n')
                for line in import_lines:
                    line = line.strip().strip('"')
                    if line and not line.startswith('//'):
                        result["imports"].append(line)
            else:
                # Single line imports
                single_imports = re.findall(r'import\s+"([^"]+)"', content)
                result["imports"].extend(single_imports)
            
            # Extract function names
            function_matches = re.findall(r'func\s+(\w+)\s*\(', content)
            result["functions"] = function_matches
            
            # Extract type definitions
            type_matches = re.findall(r'type\s+(\w+)\s+(?:struct|interface)', content)
            result["types"] = type_matches
            
            return result
            
        except FileNotFoundError:
            return {"error": "File not found"}
        except Exception as e:
            return {"error": str(e)}