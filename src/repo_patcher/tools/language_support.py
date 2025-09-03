"""Language support framework for multi-language test fixing."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"
    RUST = "rust"


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    GO_TEST = "go_test"
    JUNIT = "junit"
    XUNIT = "xunit"
    CARGO_TEST = "cargo_test"


@dataclass
class LanguageConfig:
    """Configuration for a specific language."""
    language: Language
    test_frameworks: List[TestFramework]
    file_extensions: List[str]
    dependency_files: List[str]
    common_imports: Dict[str, str]
    test_patterns: List[str]
    ignore_patterns: List[str]


@dataclass
class TestFrameworkConfig:
    """Configuration for a specific test framework."""
    framework: TestFramework
    language: Language
    command_template: str
    config_files: List[str]
    test_file_patterns: List[str]
    result_parser_class: str


class BaseLanguageHandler(ABC):
    """Base class for language-specific handlers."""
    
    def __init__(self, config: LanguageConfig):
        self.config = config
        self.language = config.language
    
    @abstractmethod
    def detect_framework(self, repo_path: Path) -> Optional[TestFramework]:
        """Detect the test framework used in the repository."""
        pass
    
    @abstractmethod
    def get_test_command(self, repo_path: Path, framework: TestFramework) -> str:
        """Get the test command for the framework."""
        pass
    
    @abstractmethod
    def parse_test_output(self, stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
        """Parse test framework output into structured format."""
        pass
    
    @abstractmethod
    def get_dependency_info(self, repo_path: Path) -> Dict[str, Any]:
        """Get dependency information from package files."""
        pass
    
    @abstractmethod
    def suggest_imports(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Suggest import statements based on error messages."""
        pass
    
    def get_file_extensions(self) -> List[str]:
        """Get file extensions for this language."""
        return self.config.file_extensions
    
    def is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file based on patterns."""
        file_str = str(file_path)
        return any(pattern in file_str for pattern in self.config.test_patterns)
    
    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored."""
        file_str = str(file_path)
        return any(pattern in file_str for pattern in self.config.ignore_patterns)


# Language configurations
PYTHON_CONFIG = LanguageConfig(
    language=Language.PYTHON,
    test_frameworks=[TestFramework.PYTEST],
    file_extensions=[".py"],
    dependency_files=["requirements.txt", "pyproject.toml", "setup.py"],
    common_imports={
        "sqrt": "from math import sqrt",
        "randint": "from random import randint",
        "datetime": "from datetime import datetime",
        "json": "import json",
        "re": "import re",
        "os": "import os",
        "sys": "import sys",
        "Path": "from pathlib import Path"
    },
    test_patterns=["test_", "_test.py", "/tests/"],
    ignore_patterns=[".git/", "__pycache__/", ".pytest_cache/", "node_modules/"]
)

JAVASCRIPT_CONFIG = LanguageConfig(
    language=Language.JAVASCRIPT,
    test_frameworks=[TestFramework.JEST, TestFramework.MOCHA, TestFramework.VITEST],
    file_extensions=[".js", ".jsx"],
    dependency_files=["package.json", "package-lock.json", "yarn.lock"],
    common_imports={
        "React": "import React from 'react';",
        "useState": "import { useState } from 'react';",
        "useEffect": "import { useEffect } from 'react';",
        "axios": "import axios from 'axios';",
        "lodash": "import _ from 'lodash';",
        "moment": "import moment from 'moment';"
    },
    test_patterns=[".test.js", ".spec.js", "__tests__/"],
    ignore_patterns=[".git/", "node_modules/", "dist/", "build/"]
)

TYPESCRIPT_CONFIG = LanguageConfig(
    language=Language.TYPESCRIPT,
    test_frameworks=[TestFramework.JEST, TestFramework.MOCHA, TestFramework.VITEST],
    file_extensions=[".ts", ".tsx"],
    dependency_files=["package.json", "package-lock.json", "yarn.lock", "tsconfig.json"],
    common_imports={
        "React": "import React from 'react';",
        "useState": "import { useState } from 'react';",
        "useEffect": "import { useEffect } from 'react';",
        "axios": "import axios from 'axios';",
        "lodash": "import _ from 'lodash';",
        "moment": "import moment from 'moment';"
    },
    test_patterns=[".test.ts", ".spec.ts", "__tests__/"],
    ignore_patterns=[".git/", "node_modules/", "dist/", "build/"]
)

GO_CONFIG = LanguageConfig(
    language=Language.GO,
    test_frameworks=[TestFramework.GO_TEST],
    file_extensions=[".go"],
    dependency_files=["go.mod", "go.sum"],
    common_imports={
        "fmt": "import \"fmt\"",
        "testing": "import \"testing\"",
        "errors": "import \"errors\"",
        "context": "import \"context\"",
        "time": "import \"time\"",
        "json": "import \"encoding/json\""
    },
    test_patterns=["_test.go"],
    ignore_patterns=[".git/", "vendor/"]
)


class LanguageDetector:
    """Detects the programming language of a repository."""
    
    LANGUAGE_CONFIGS = {
        Language.PYTHON: PYTHON_CONFIG,
        Language.JAVASCRIPT: JAVASCRIPT_CONFIG,
        Language.TYPESCRIPT: TYPESCRIPT_CONFIG,
        Language.GO: GO_CONFIG
    }
    
    @classmethod
    def detect_language(cls, repo_path: Path) -> Optional[Language]:
        """Detect the primary language of the repository."""
        language_scores = {}
        
        # Check for language-specific files
        for language, config in cls.LANGUAGE_CONFIGS.items():
            score = 0
            
            # Check for dependency files
            for dep_file in config.dependency_files:
                if (repo_path / dep_file).exists():
                    score += 10
            
            # Count source files
            source_files = 0
            for ext in config.file_extensions:
                source_files += len(list(repo_path.rglob(f"*{ext}")))
            
            score += source_files
            
            if score > 0:
                language_scores[language] = score
        
        if not language_scores:
            return None
        
        # Return language with highest score
        return max(language_scores, key=language_scores.get)
    
    @classmethod
    def get_config(cls, language: Language) -> LanguageConfig:
        """Get configuration for a language."""
        return cls.LANGUAGE_CONFIGS[language]


class MultiLanguageTestRunner:
    """Test runner that supports multiple programming languages."""
    
    def __init__(self):
        self.handlers = {}
    
    def get_handler(self, language: Language) -> BaseLanguageHandler:
        """Get or create handler for a language."""
        if language not in self.handlers:
            config = LanguageDetector.get_config(language)
            
            if language == Language.PYTHON:
                from .python_handler import PythonHandler
                self.handlers[language] = PythonHandler(config)
            elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
                from .javascript_handler import JavaScriptHandler
                self.handlers[language] = JavaScriptHandler(config)
            elif language == Language.GO:
                from .go_handler import GoHandler
                self.handlers[language] = GoHandler(config)
            else:
                raise ValueError(f"Unsupported language: {language}")
        
        return self.handlers[language]
    
    def analyze_repository(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze a repository to determine language and test setup."""
        language = LanguageDetector.detect_language(repo_path)
        
        if not language:
            return {
                "error": "Could not detect programming language",
                "supported_languages": [lang.value for lang in Language]
            }
        
        handler = self.get_handler(language)
        framework = handler.detect_framework(repo_path)
        
        return {
            "language": language.value,
            "framework": framework.value if framework else None,
            "test_command": handler.get_test_command(repo_path, framework) if framework else None,
            "dependencies": handler.get_dependency_info(repo_path),
            "file_extensions": handler.get_file_extensions(),
            "handler": handler.__class__.__name__
        }