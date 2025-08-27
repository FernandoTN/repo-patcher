"""Core state machine for the test fixing agent."""
import logging
import time
import uuid
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

from .models import (
    AgentSession, 
    AgentState, 
    StepResult, 
    StepExecution,
    RepositoryContext
)
from .openai_client import OpenAIClient, INGEST_SCHEMA
from .exceptions import AIClientError, ConfigurationError
from .shutdown import managed_operation, operation_timeout

logger = logging.getLogger(__name__)


class StateHandler(ABC):
    """Abstract base class for state handlers."""
    
    @abstractmethod
    async def execute(self, session: AgentSession) -> StepResult:
        """Execute the state logic."""
        pass
    
    @abstractmethod
    def get_state(self) -> AgentState:
        """Return the state this handler manages."""
        pass


class IngestHandler(StateHandler):
    """Handler for the INGEST state - analyze repository and failing tests."""
    
    def __init__(self, ai_client: Optional[OpenAIClient] = None):
        self.ai_client = ai_client
    
    def get_state(self) -> AgentState:
        return AgentState.INGEST
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Ingest repository information and identify failing tests."""
        logger.info(f"Ingesting repository: {session.repository.repo_path}")
        
        async with managed_operation("ingest_repository"):
            async with operation_timeout(session.config.state_timeout, "ingest"):
                try:
                    # Step 1: Analyze repository structure
                    repo_structure = await self._analyze_repo_structure(session.repository.repo_path)
                    
                    # Step 2: Run tests to identify failures if not already provided
                    if not session.repository.failing_tests:
                        test_results = await self._run_initial_tests(session)
                    else:
                        test_results = {
                            "failing_tests": session.repository.failing_tests,
                            "test_output": session.repository.test_output
                        }
                    
                    # Step 3: Use AI to analyze failures and repository context
                    if self.ai_client:
                        analysis_result = await self._ai_analyze_failures(
                            repo_structure, test_results, session
                        )
                        
                        # Store analysis in session context
                        session.context.add_code_context("ingest_analysis", analysis_result)
                        
                        # Update repository with analyzed failures
                        if analysis_result.get("failing_tests"):
                            session.repository.failing_tests = [
                                test["test_name"] for test in analysis_result["failing_tests"]
                            ]
                    
                    input_data = {
                        "repo_path": str(session.repository.repo_path),
                        "structure_files": len(repo_structure.get("files", [])),
                        "failing_tests_count": len(session.repository.failing_tests)
                    }
                    
                    output_data = {
                        "structure_analyzed": True,
                        "failing_tests": len(session.repository.failing_tests),
                        "ai_analysis_available": self.ai_client is not None
                    }
                    
                    return StepResult.SUCCESS
                    
                except Exception as e:
                    logger.error(f"Error in ingest handler: {e}")
                    raise
    
    async def _analyze_repo_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository file structure and dependencies."""
        structure = {
            "files": [],
            "test_files": [],
            "src_files": [],
            "imports": [],
            "dependencies": []
        }
        
        try:
            # Walk through repository files
            for root, dirs, files in os.walk(repo_path):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.go', '.java')):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(repo_path)
                        
                        structure["files"].append(str(rel_path))
                        
                        if "test" in file.lower() or "spec" in file.lower():
                            structure["test_files"].append(str(rel_path))
                        else:
                            structure["src_files"].append(str(rel_path))
                        
                        # Basic import analysis for Python files
                        if file.endswith('.py'):
                            imports = await self._extract_imports(file_path)
                            structure["imports"].extend(imports)
            
            # Look for dependency files
            for dep_file in ["requirements.txt", "pyproject.toml", "package.json", "go.mod", "pom.xml"]:
                if (repo_path / dep_file).exists():
                    structure["dependencies"].append(dep_file)
            
            logger.info(f"Repository structure: {len(structure['files'])} files, {len(structure['test_files'])} test files")
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            return structure
    
    async def _extract_imports(self, file_path: Path) -> list:
        """Extract import statements from a Python file."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        imports.append({
                            "statement": line,
                            "file": str(file_path),
                            "line": line_no
                        })
                        if len(imports) > 50:  # Limit to avoid too much data
                            break
        except Exception as e:
            logger.debug(f"Could not extract imports from {file_path}: {e}")
        
        return imports
    
    async def _run_initial_tests(self, session: AgentSession) -> Dict[str, Any]:
        """Run tests to identify failures."""
        logger.info(f"Running tests: {session.repository.test_command}")
        
        try:
            result = subprocess.run(
                session.repository.test_command.split(),
                cwd=session.repository.repo_path,
                capture_output=True,
                text=True,
                timeout=session.config.test_timeout
            )
            
            test_output = result.stdout + "\n" + result.stderr
            session.repository.test_output = test_output
            
            # Parse failing tests from output (basic implementation)
            failing_tests = self._parse_test_failures(test_output, session.repository.test_framework)
            
            return {
                "exit_code": result.returncode,
                "failing_tests": failing_tests,
                "test_output": test_output,
                "passed": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Test execution timed out after {session.config.test_timeout}s")
            return {
                "exit_code": -1,
                "failing_tests": [],
                "test_output": "Test execution timed out",
                "passed": False
            }
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "exit_code": -1,
                "failing_tests": [],
                "test_output": str(e),
                "passed": False
            }
    
    def _parse_test_failures(self, output: str, framework: str) -> list:
        """Parse test failures from output based on framework."""
        failures = []
        
        if framework.lower() in ["pytest", "python"]:
            # Basic pytest failure parsing
            lines = output.split('\n')
            for line in lines:
                if "FAILED" in line and "::" in line:
                    test_name = line.split()[0] if line.split() else line
                    failures.append(test_name)
        
        # Add more framework parsers as needed
        
        return failures
    
    async def _ai_analyze_failures(self, repo_structure: Dict[str, Any], test_results: Dict[str, Any], session: AgentSession) -> Dict[str, Any]:
        """Use AI to analyze test failures and repository context."""
        if not self.ai_client:
            return {}
        
        # Prepare context for AI analysis
        context = f"""
Repository Analysis:
- Total files: {len(repo_structure.get('files', []))}
- Source files: {len(repo_structure.get('src_files', []))}
- Test files: {len(repo_structure.get('test_files', []))}
- Dependencies: {', '.join(repo_structure.get('dependencies', []))}

Test Results:
- Exit code: {test_results.get('exit_code', 'unknown')}
- Failing tests: {test_results.get('failing_tests', [])}

Test Output:
{test_results.get('test_output', '')[:2000]}...

Key Files:
{repo_structure.get('src_files', [])[:10]}

Sample Imports:
{repo_structure.get('imports', [])[:10]}
"""
        
        messages = [
            {
                "role": "user",
                "content": f"Analyze this repository and its failing tests. Provide a structured analysis.\n\n{context}"
            }
        ]
        
        system_prompt = """You are a senior software engineer analyzing a repository with failing tests. 
Provide a structured analysis including:
1. List of failing tests with error categorization
2. Root cause analysis 
3. Affected files and dependencies
4. Code context (imports, functions, classes)
5. Complexity assessment

Focus on actionable insights for fixing the tests."""
        
        try:
            response = await self.ai_client.complete_with_schema(
                messages=messages,
                schema=INGEST_SCHEMA,
                system_prompt=system_prompt
            )
            
            if response.is_valid_json():
                logger.info(f"AI analysis completed successfully. Cost: ${response.token_usage.estimated_cost:.4f}")
                return response.parsed_data
            else:
                logger.warning("AI analysis did not return valid JSON")
                return {}
                
        except AIClientError as e:
            logger.error(f"AI analysis failed: {e}")
            return {}


class PlanHandler(StateHandler):
    """Handler for the PLAN state - create fix strategy."""
    
    def get_state(self) -> AgentState:
        return AgentState.PLAN
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Create a plan for fixing the failing tests."""
        logger.info(f"Planning fixes for {len(session.repository.failing_tests)} failing tests")
        
        # TODO: Implement actual planning logic
        # - Analyze error messages
        # - Search codebase for relevant files
        # - Generate fix strategy
        # - Create step-by-step plan
        
        # Mock implementation for now
        input_data = {
            "failing_tests": session.repository.failing_tests,
            "iteration": session.iteration_count
        }
        output_data = {"plan_created": True}
        
        return StepResult.SUCCESS


class PatchHandler(StateHandler):
    """Handler for the PATCH state - apply code changes."""
    
    def get_state(self) -> AgentState:
        return AgentState.PATCH
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Apply the planned patches to fix the tests."""
        logger.info(f"Applying patches based on plan")
        
        # TODO: Implement actual patching logic
        # - Generate code changes
        # - Apply patches safely
        # - Create git commits
        # - Validate changes
        
        # Mock implementation for now
        input_data = {"plan": session.plan}
        output_data = {"patches_applied": len(session.patches)}
        
        return StepResult.SUCCESS


class TestHandler(StateHandler):
    """Handler for the TEST state - run tests and validate fixes."""
    
    def get_state(self) -> AgentState:
        return AgentState.TEST
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Run tests to validate the fixes."""
        logger.info("Running tests to validate fixes")
        
        # TODO: Implement actual test execution
        # - Run test suite
        # - Parse results
        # - Determine if fixes worked
        # - Collect new failures if any
        
        # Mock implementation for now - simulate success
        input_data = {"test_command": session.repository.test_command}
        output_data = {"tests_passed": True, "all_tests_pass": True}
        
        # For now, let's simulate success to test the flow
        return StepResult.SUCCESS


class RepairHandler(StateHandler):
    """Handler for the REPAIR state - fix issues from failed tests."""
    
    def get_state(self) -> AgentState:
        return AgentState.REPAIR
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Analyze test failures and prepare for another iteration."""
        logger.info(f"Repairing - iteration {session.iteration_count + 1}")
        
        # TODO: Implement actual repair logic
        # - Analyze what went wrong
        # - Update context with new failures
        # - Decide whether to retry or escalate
        
        # Mock implementation for now
        input_data = {"iteration": session.iteration_count}
        
        if session.iteration_count >= session.max_iterations:
            output_data = {"decision": "escalate"}
            return StepResult.ESCALATE
        else:
            output_data = {"decision": "retry"}
            return StepResult.RETRY


class PRHandler(StateHandler):
    """Handler for the PR state - create pull request."""
    
    def get_state(self) -> AgentState:
        return AgentState.PR
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Create a pull request with the fixes."""
        logger.info("Creating pull request with fixes")
        
        # TODO: Implement actual PR creation
        # - Generate PR title and description
        # - Create branch
        # - Push changes
        # - Open PR via GitHub API
        
        # Mock implementation for now
        input_data = {"patches": len(session.patches)}
        output_data = {"pr_url": "https://github.com/example/repo/pull/123"}
        
        return StepResult.SUCCESS


class AgentStateMachine:
    """Main state machine orchestrating the agent workflow."""
    
    def __init__(self, ai_client: Optional[OpenAIClient] = None):
        self.ai_client = ai_client
        self.handlers: Dict[AgentState, StateHandler] = {
            AgentState.INGEST: IngestHandler(ai_client),
            AgentState.PLAN: PlanHandler(),
            AgentState.PATCH: PatchHandler(),
            AgentState.TEST: TestHandler(),
            AgentState.REPAIR: RepairHandler(),
            AgentState.PR: PRHandler(),
        }
    
    async def execute_session(self, repository: RepositoryContext) -> AgentSession:
        """Execute a complete agent session."""
        session = AgentSession(
            session_id=str(uuid.uuid4()),
            repository=repository,
            current_state=AgentState.INGEST
        )
        
        logger.info(f"Starting agent session {session.session_id}")
        
        while not session.is_complete:
            result = await self._execute_step(session)
            
            # Safety check to prevent infinite loops
            if len(session.executions) > 20:
                logger.error("Too many execution steps, escalating")
                session.current_state = AgentState.ESCALATED
                break
        
        session.end_time = time.time()
        logger.info(f"Session {session.session_id} completed in state {session.current_state.value}")
        
        return session
    
    async def _execute_step(self, session: AgentSession) -> StepResult:
        """Execute a single step in the state machine."""
        current_state = session.current_state
        
        if current_state not in self.handlers:
            logger.error(f"No handler for state {current_state}")
            session.current_state = AgentState.FAILED
            return StepResult.FAILURE
        
        handler = self.handlers[current_state]
        start_time = time.time()
        
        try:
            result = await handler.execute(session)
            duration = time.time() - start_time
            
            execution = StepExecution(
                state=current_state,
                result=result,
                duration=duration,
                input_data={"state": current_state.value},
                output_data={"result": result.value}
            )
            
            session.add_execution(execution)
            
            logger.info(f"State {current_state.value} completed with result {result.value}")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in state {current_state.value}: {e}")
            
            execution = StepExecution(
                state=current_state,
                result=StepResult.FAILURE,
                duration=duration,
                input_data={"state": current_state.value},
                output_data={},
                error_message=str(e)
            )
            
            session.add_execution(execution)
            session.current_state = AgentState.FAILED
            
            return StepResult.FAILURE