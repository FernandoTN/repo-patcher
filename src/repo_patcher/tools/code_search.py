"""Code search tool for semantic repository understanding."""
import os
import re
import ast
import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class CodeMatch:
    """Represents a code search match."""
    file_path: str
    line_number: int
    content: str
    context_before: List[str]
    context_after: List[str]
    match_type: str  # "function", "class", "import", "variable", "string"


@dataclass 
class FunctionInfo:
    """Information about a function."""
    name: str
    file_path: str
    line_number: int
    parameters: List[str]
    return_annotation: Optional[str]
    docstring: Optional[str]
    is_async: bool


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    file_path: str
    line_number: int
    methods: List[str]
    base_classes: List[str]
    docstring: Optional[str]


class CodeSearchTool(BaseTool):
    """Tool for semantic code search and repository understanding."""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
        self.ignore_patterns = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules', 
            '.venv', 'venv', '.env', 'dist', 'build', '.DS_Store'
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute code search operation."""
        operation = kwargs.get('operation', 'search')
        repo_path = Path(kwargs.get('repo_path', '.'))
        
        if operation == 'search':
            return await self._search_code(repo_path, kwargs)
        elif operation == 'analyze_structure':
            return await self._analyze_repository_structure(repo_path)
        elif operation == 'find_functions':
            return await self._find_functions(repo_path, kwargs.get('pattern', ''))
        elif operation == 'find_classes':
            return await self._find_classes(repo_path, kwargs.get('pattern', ''))
        elif operation == 'analyze_imports':
            return await self._analyze_imports(repo_path)
        else:
            return ToolResult(
                success=False,
                data={},
                error=f"Unsupported operation: {operation}",
                cost=0.0
            )
    
    async def _search_code(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Search for code patterns in repository."""
        query = params.get('query', '')
        file_pattern = params.get('file_pattern', '*')
        max_results = params.get('max_results', 50)
        context_lines = params.get('context_lines', 3)
        
        if not query:
            return ToolResult(
                success=False,
                data={},
                error="Search query is required",
                cost=0.0
            )
        
        matches = []
        files_searched = 0
        
        try:
            for file_path in self._find_source_files(repo_path, file_pattern):
                files_searched += 1
                file_matches = await self._search_in_file(
                    file_path, query, context_lines
                )
                matches.extend(file_matches)
                
                if len(matches) >= max_results:
                    matches = matches[:max_results]
                    break
            
            return ToolResult(
                success=True,
                data={
                    'matches': [self._match_to_dict(match) for match in matches],
                    'total_matches': len(matches),
                    'files_searched': files_searched,
                    'query': query
                },
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Code search failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _analyze_repository_structure(self, repo_path: Path) -> ToolResult:
        """Analyze overall repository structure."""
        try:
            structure = {
                'source_files': [],
                'test_files': [],
                'config_files': [],
                'documentation_files': [],
                'total_files': 0,
                'total_lines': 0,
                'languages': set(),
                'directories': []
            }
            
            for file_path in self._find_all_files(repo_path):
                relative_path = str(file_path.relative_to(repo_path))
                extension = file_path.suffix.lower()
                
                structure['total_files'] += 1
                
                # Count lines
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        structure['total_lines'] += lines
                except:
                    continue
                
                # Categorize files
                if self._is_test_file(file_path):
                    structure['test_files'].append(relative_path)
                elif extension in self.supported_extensions:
                    structure['source_files'].append(relative_path)
                    structure['languages'].add(self._detect_language(extension))
                elif self._is_config_file(file_path):
                    structure['config_files'].append(relative_path)
                elif self._is_documentation_file(file_path):
                    structure['documentation_files'].append(relative_path)
            
            # Convert set to list for JSON serialization
            structure['languages'] = list(structure['languages'])
            
            # Get directory structure
            structure['directories'] = self._get_directory_structure(repo_path)
            
            return ToolResult(
                success=True,
                data=structure,
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Repository structure analysis failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _find_functions(self, repo_path: Path, pattern: str = '') -> ToolResult:
        """Find all functions in Python files."""
        functions = []
        
        try:
            for file_path in self._find_source_files(repo_path, '*.py'):
                file_functions = self._extract_functions_from_python_file(file_path)
                
                if pattern:
                    file_functions = [
                        f for f in file_functions 
                        if re.search(pattern, f.name, re.IGNORECASE)
                    ]
                
                functions.extend(file_functions)
            
            return ToolResult(
                success=True,
                data={
                    'functions': [self._function_to_dict(func) for func in functions],
                    'total_functions': len(functions),
                    'pattern': pattern
                },
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Function search failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _find_classes(self, repo_path: Path, pattern: str = '') -> ToolResult:
        """Find all classes in Python files."""
        classes = []
        
        try:
            for file_path in self._find_source_files(repo_path, '*.py'):
                file_classes = self._extract_classes_from_python_file(file_path)
                
                if pattern:
                    file_classes = [
                        c for c in file_classes 
                        if re.search(pattern, c.name, re.IGNORECASE)
                    ]
                
                classes.extend(file_classes)
            
            return ToolResult(
                success=True,
                data={
                    'classes': [self._class_to_dict(cls) for cls in classes],
                    'total_classes': len(classes),
                    'pattern': pattern
                },
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Class search failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _analyze_imports(self, repo_path: Path) -> ToolResult:
        """Analyze import dependencies in Python files."""
        imports = {
            'standard_library': set(),
            'third_party': set(),
            'local': set(),
            'import_map': {},  # file -> list of imports
            'dependency_graph': {}  # module -> list of dependencies
        }
        
        try:
            for file_path in self._find_source_files(repo_path, '*.py'):
                file_imports = self._extract_imports_from_python_file(file_path)
                relative_path = str(file_path.relative_to(repo_path))
                
                imports['import_map'][relative_path] = file_imports
                
                for imp in file_imports:
                    if self._is_standard_library_import(imp):
                        imports['standard_library'].add(imp)
                    elif self._is_local_import(imp, repo_path):
                        imports['local'].add(imp)
                    else:
                        imports['third_party'].add(imp)
            
            # Convert sets to lists for JSON serialization
            imports['standard_library'] = list(imports['standard_library'])
            imports['third_party'] = list(imports['third_party'])
            imports['local'] = list(imports['local'])
            
            return ToolResult(
                success=True,
                data=imports,
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Import analysis failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    def _find_all_files(self, repo_path: Path) -> List[Path]:
        """Find all files in repository, excluding ignored patterns."""
        files = []
        
        for root, dirs, filenames in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_path(d)]
            
            for filename in filenames:
                if not self._should_ignore_path(filename):
                    files.append(Path(root) / filename)
        
        return files
    
    def _find_source_files(self, repo_path: Path, pattern: str = '*') -> List[Path]:
        """Find source files matching pattern."""
        files = []
        
        if pattern == '*':
            # Find all supported source files
            for file_path in self._find_all_files(repo_path):
                if file_path.suffix.lower() in self.supported_extensions:
                    files.append(file_path)
        else:
            # Use pattern matching (simplified)
            import fnmatch
            for file_path in self._find_all_files(repo_path):
                if fnmatch.fnmatch(file_path.name, pattern):
                    files.append(file_path)
        
        return files
    
    async def _search_in_file(self, file_path: Path, query: str, context_lines: int) -> List[CodeMatch]:
        """Search for query in a single file."""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if re.search(query, line, re.IGNORECASE):
                    # Get context
                    start_idx = max(0, i - context_lines)
                    end_idx = min(len(lines), i + context_lines + 1)
                    
                    context_before = [lines[j].rstrip() for j in range(start_idx, i)]
                    context_after = [lines[j].rstrip() for j in range(i + 1, end_idx)]
                    
                    match = CodeMatch(
                        file_path=str(file_path),
                        line_number=i + 1,
                        content=line.rstrip(),
                        context_before=context_before,
                        context_after=context_after,
                        match_type=self._detect_match_type(line)
                    )
                    matches.append(match)
                    
        except Exception as e:
            logger.warning(f"Error searching in {file_path}: {e}")
        
        return matches
    
    def _extract_functions_from_python_file(self, file_path: Path) -> List[FunctionInfo]:
        """Extract function information from Python file using AST."""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Extract parameters
                    params = [arg.arg for arg in node.args.args]
                    
                    # Extract return annotation
                    return_annotation = None
                    if node.returns:
                        return_annotation = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                    
                    # Extract docstring
                    docstring = None
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring = node.body[0].value.value
                    
                    function = FunctionInfo(
                        name=node.name,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        parameters=params,
                        return_annotation=return_annotation,
                        docstring=docstring,
                        is_async=isinstance(node, ast.AsyncFunctionDef)
                    )
                    functions.append(function)
                    
        except Exception as e:
            logger.warning(f"Error extracting functions from {file_path}: {e}")
        
        return functions
    
    def _extract_classes_from_python_file(self, file_path: Path) -> List[ClassInfo]:
        """Extract class information from Python file using AST."""
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract methods
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append(item.name)
                    
                    # Extract base classes
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif hasattr(ast, 'unparse'):
                            base_classes.append(ast.unparse(base))
                    
                    # Extract docstring
                    docstring = None
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring = node.body[0].value.value
                    
                    cls = ClassInfo(
                        name=node.name,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        methods=methods,
                        base_classes=base_classes,
                        docstring=docstring
                    )
                    classes.append(cls)
                    
        except Exception as e:
            logger.warning(f"Error extracting classes from {file_path}: {e}")
        
        return classes
    
    def _extract_imports_from_python_file(self, file_path: Path) -> List[str]:
        """Extract import statements from Python file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except Exception as e:
            logger.warning(f"Error extracting imports from {file_path}: {e}")
        
        return imports
    
    def _should_ignore_path(self, path_part: str) -> bool:
        """Check if path should be ignored."""
        return any(pattern in path_part for pattern in self.ignore_patterns)
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        name = file_path.name.lower()
        return (name.startswith('test_') or 
                name.endswith('_test.py') or 
                'test' in file_path.parts)
    
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file."""
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'}
        config_names = {'setup.py', 'setup.cfg', 'pyproject.toml', 'requirements.txt'}
        
        return (file_path.suffix.lower() in config_extensions or 
                file_path.name in config_names)
    
    def _is_documentation_file(self, file_path: Path) -> bool:
        """Check if file is documentation."""
        doc_extensions = {'.md', '.rst', '.txt'}
        return file_path.suffix.lower() in doc_extensions
    
    def _detect_language(self, extension: str) -> str:
        """Detect programming language from file extension."""
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++ Header'
        }
        return lang_map.get(extension.lower(), 'Unknown')
    
    def _detect_match_type(self, line: str) -> str:
        """Detect what type of code construct the match is."""
        line = line.strip()
        
        if line.startswith('def ') or line.startswith('async def '):
            return 'function'
        elif line.startswith('class '):
            return 'class'
        elif line.startswith('import ') or line.startswith('from '):
            return 'import'
        elif '=' in line and not line.startswith('#'):
            return 'variable'
        else:
            return 'string'
    
    def _get_directory_structure(self, repo_path: Path) -> List[str]:
        """Get list of directories in repository."""
        directories = []
        for root, dirs, _ in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not self._should_ignore_path(d)]
            for directory in dirs:
                rel_path = str(Path(root).relative_to(repo_path) / directory)
                directories.append(rel_path)
        return sorted(directories)
    
    def _is_standard_library_import(self, import_name: str) -> bool:
        """Check if import is from Python standard library."""
        # Simplified check - in production, use stdlib_list package
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'collections',
            'itertools', 'functools', 'pathlib', 'typing', 'asyncio',
            'logging', 'unittest', 'subprocess', 'threading', 'multiprocessing'
        }
        return import_name.split('.')[0] in stdlib_modules
    
    def _is_local_import(self, import_name: str, repo_path: Path) -> bool:
        """Check if import is a local module."""
        # Check if corresponding Python file exists in repository
        import_path = repo_path / f"{import_name.replace('.', '/')}.py"
        return import_path.exists()
    
    def _match_to_dict(self, match: CodeMatch) -> Dict[str, Any]:
        """Convert CodeMatch to dictionary."""
        return {
            'file_path': match.file_path,
            'line_number': match.line_number,
            'content': match.content,
            'context_before': match.context_before,
            'context_after': match.context_after,
            'match_type': match.match_type
        }
    
    def _function_to_dict(self, func: FunctionInfo) -> Dict[str, Any]:
        """Convert FunctionInfo to dictionary."""
        return {
            'name': func.name,
            'file_path': func.file_path,
            'line_number': func.line_number,
            'parameters': func.parameters,
            'return_annotation': func.return_annotation,
            'docstring': func.docstring,
            'is_async': func.is_async
        }
    
    def _class_to_dict(self, cls: ClassInfo) -> Dict[str, Any]:
        """Convert ClassInfo to dictionary."""
        return {
            'name': cls.name,
            'file_path': cls.file_path,
            'line_number': cls.line_number,
            'methods': cls.methods,
            'base_classes': cls.base_classes,
            'docstring': cls.docstring
        }
    
    def _calculate_cost(self, **kwargs) -> float:
        """Code search operations are free."""
        return 0.0