"""Core state machine for the test fixing agent."""
import logging
import time
import uuid
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from .models import (
    AgentSession, 
    AgentState, 
    StepResult, 
    StepExecution,
    RepositoryContext
)
from .openai_client import OpenAIClient, INGEST_SCHEMA, PLAN_SCHEMA, PATCH_SCHEMA
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
    
    def __init__(self, ai_client: Optional[OpenAIClient] = None):
        self.ai_client = ai_client
    
    def get_state(self) -> AgentState:
        return AgentState.PLAN
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Create a plan for fixing the failing tests."""
        logger.info(f"Planning fixes for {len(session.repository.failing_tests)} failing tests")
        
        async with managed_operation("plan_generation"):
            async with operation_timeout(session.config.state_timeout, "plan"):
                try:
                    # Get analysis from ingest phase
                    ingest_analysis = session.context.get_code_context("ingest_analysis", {})
                    
                    if self.ai_client and ingest_analysis:
                        plan_data = await self._ai_generate_plan(ingest_analysis, session)
                        
                        # Store plan in session context
                        session.context.add_code_context("plan_data", plan_data)
                        
                        logger.info(f"AI-generated plan with {len(plan_data.get('steps', []))} steps")
                        
                    input_data = {
                        "failing_tests": session.repository.failing_tests,
                        "iteration": session.iteration_count,
                        "has_ingest_analysis": bool(ingest_analysis)
                    }
                    
                    output_data = {
                        "plan_created": True,
                        "ai_generated": self.ai_client is not None and bool(ingest_analysis),
                        "steps_count": len(session.context.get_code_context("plan_data", {}).get("steps", []))
                    }
                    
                    return StepResult.SUCCESS
                    
                except Exception as e:
                    logger.error(f"Error in plan handler: {e}")
                    raise
    
    async def _ai_generate_plan(self, ingest_analysis: Dict[str, Any], session: AgentSession) -> Dict[str, Any]:
        """Use AI to generate a fix plan based on the ingest analysis."""
        if not self.ai_client:
            return {}
        
        # Prepare context for AI planning
        failing_tests = ingest_analysis.get("failing_tests", [])
        analysis = ingest_analysis.get("analysis", {})
        code_context = ingest_analysis.get("code_context", {})
        
        context = f"""
Repository Analysis:
- Root Cause: {analysis.get('root_cause', 'Unknown')}
- Affected Files: {', '.join(analysis.get('affected_files', []))}
- Complexity Level: {analysis.get('complexity_level', 'medium')}

Failing Tests ({len(failing_tests)}):
{self._format_failing_tests(failing_tests)}

Code Context:
- Available Imports: {', '.join(code_context.get('imports', []))}
- Functions Found: {', '.join(code_context.get('functions', []))}
- Classes Found: {', '.join(code_context.get('classes', []))}

Current Iteration: {session.iteration_count}
Previous Attempts: {session.iteration_count - 1}
"""
        
        messages = [
            {
                "role": "user",
                "content": f"Create a detailed fix plan for these failing tests. Consider the root cause analysis and provide actionable steps.\n\n{context}"
            }
        ]
        
        system_prompt = """You are a senior software engineer creating a fix plan for failing tests.

Generate a comprehensive plan that includes:
1. Overall strategy description
2. Step-by-step actions to fix the issues
3. Risk assessment with confidence level

For each step, specify:
- The action to take (e.g., "add_import", "fix_syntax", "update_logic")
- Clear description of what needs to be done
- Files that will be modified
- Expected outcome

Focus on minimal, surgical changes that address the root cause."""
        
        try:
            response = await self.ai_client.complete_with_schema(
                messages=messages,
                schema=PLAN_SCHEMA,
                system_prompt=system_prompt
            )
            
            if response.is_valid_json():
                logger.info(f"AI plan generation completed. Cost: ${response.token_usage.estimated_cost:.4f}")
                return response.parsed_data
            else:
                logger.warning("AI plan generation did not return valid JSON")
                return {}
                
        except AIClientError as e:
            logger.error(f"AI plan generation failed: {e}")
            return {}
    
    def _format_failing_tests(self, failing_tests: List[Dict[str, Any]]) -> str:
        """Format failing tests for AI context."""
        if not failing_tests:
            return "No failing tests provided"
        
        formatted = []
        for test in failing_tests[:5]:  # Limit to first 5 for context
            formatted.append(
                f"- {test.get('test_name', 'unknown')}: "
                f"{test.get('error_type', 'Error')} - {test.get('error_message', 'No message')}"
            )
        
        if len(failing_tests) > 5:
            formatted.append(f"... and {len(failing_tests) - 5} more tests")
        
        return '\n'.join(formatted)


class PatchHandler(StateHandler):
    """Handler for the PATCH state - apply code changes."""
    
    def __init__(self, ai_client: Optional[OpenAIClient] = None):
        self.ai_client = ai_client
    
    def get_state(self) -> AgentState:
        return AgentState.PATCH
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Apply the planned patches to fix the tests."""
        logger.info(f"Applying patches based on plan")
        
        async with managed_operation("patch_application"):
            async with operation_timeout(session.config.state_timeout, "patch"):
                try:
                    # Get plan from previous phase
                    plan_data = session.context.get_code_context("plan_data", {})
                    
                    if self.ai_client and plan_data:
                        patch_data = await self._ai_generate_patches(plan_data, session)
                        
                        # Store patches in session context
                        session.context.add_code_context("patch_data", patch_data)
                        
                        # Apply the patches safely
                        applied_patches = await self._apply_patches_safely(patch_data, session)
                        
                        logger.info(f"Successfully applied {len(applied_patches)} patches")
                    
                    input_data = {
                        "has_plan": bool(plan_data),
                        "plan_steps": len(plan_data.get("steps", []))
                    }
                    
                    output_data = {
                        "patches_applied": len(session.context.get_code_context("patch_data", {}).get("changes", [])),
                        "ai_generated": self.ai_client is not None and bool(plan_data)
                    }
                    
                    return StepResult.SUCCESS
                    
                except Exception as e:
                    logger.error(f"Error in patch handler: {e}")
                    raise
    
    async def _ai_generate_patches(self, plan_data: Dict[str, Any], session: AgentSession) -> Dict[str, Any]:
        """Use AI to generate specific code patches based on the plan."""
        if not self.ai_client:
            return {}
        
        # Get additional context
        ingest_analysis = session.context.get_code_context("ingest_analysis", {})
        
        # Read relevant files to understand current code
        affected_files = []
        for step in plan_data.get("steps", []):
            for file_path in step.get("files", []):
                try:
                    full_path = session.repository.repo_path / file_path
                    if full_path.exists() and full_path.is_file():
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            affected_files.append({
                                "path": file_path,
                                "content": content[:2000],  # Limit content for context
                                "lines": len(content.split('\n'))
                            })
                except Exception as e:
                    logger.warning(f"Could not read file {file_path}: {e}")
        
        context = f"""
Fix Plan:
Strategy: {plan_data.get('strategy', 'No strategy provided')}

Steps to implement:
{self._format_plan_steps(plan_data.get('steps', []))}

Risk Assessment:
- Risk Level: {plan_data.get('risk_assessment', {}).get('risk_level', 'unknown')}
- Confidence: {plan_data.get('risk_assessment', {}).get('confidence', 'unknown')}

Current Code Files:
{self._format_file_contents(affected_files)}

Root Cause from Analysis: {ingest_analysis.get('analysis', {}).get('root_cause', 'Unknown')}
"""
        
        messages = [
            {
                "role": "user", 
                "content": f"Generate specific code changes to implement this fix plan. Provide exact line-by-line modifications.\n\n{context}"
            }
        ]
        
        system_prompt = """You are a senior software engineer implementing code fixes.

Generate precise code modifications including:
1. Exact file paths to modify
2. Specific line numbers and content changes
3. Clear operation type (replace, insert, delete)

Rules:
- Make minimal, surgical changes
- Preserve existing code style and formatting
- Focus only on fixing the identified issues
- Ensure changes are syntactically correct
- Add necessary imports if missing

Each modification should specify the exact old content and new content."""
        
        try:
            response = await self.ai_client.complete_with_schema(
                messages=messages,
                schema=PATCH_SCHEMA,
                system_prompt=system_prompt
            )
            
            if response.is_valid_json():
                logger.info(f"AI patch generation completed. Cost: ${response.token_usage.estimated_cost:.4f}")
                return response.parsed_data
            else:
                logger.warning("AI patch generation did not return valid JSON")
                return {}
                
        except AIClientError as e:
            logger.error(f"AI patch generation failed: {e}")
            return {}
    
    async def _apply_patches_safely(self, patch_data: Dict[str, Any], session: AgentSession) -> List[str]:
        """Apply patches safely with backup and validation."""
        applied_patches = []
        
        for change in patch_data.get("changes", []):
            file_path = change.get("file_path", "")
            if not file_path:
                continue
                
            full_path = session.repository.repo_path / file_path
            
            try:
                # Backup original file
                backup_path = full_path.with_suffix(f"{full_path.suffix}.backup")
                if full_path.exists():
                    import shutil
                    shutil.copy2(full_path, backup_path)
                
                # Apply modifications
                if await self._apply_file_modifications(full_path, change.get("modifications", [])):
                    applied_patches.append(file_path)
                    logger.info(f"Successfully modified {file_path}")
                else:
                    logger.warning(f"Failed to modify {file_path}")
                    
            except Exception as e:
                logger.error(f"Error applying patch to {file_path}: {e}")
                # Restore from backup if needed
                if backup_path.exists():
                    import shutil
                    shutil.copy2(backup_path, full_path)
        
        return applied_patches
    
    async def _apply_file_modifications(self, file_path: Path, modifications: List[Dict[str, Any]]) -> bool:
        """Apply modifications to a single file."""
        try:
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Sort modifications by line number in reverse order
            # This ensures line numbers remain valid during modification
            sorted_mods = sorted(modifications, key=lambda x: x.get("line_number", 0), reverse=True)
            
            for mod in sorted_mods:
                line_num = mod.get("line_number", 0)
                old_content = mod.get("old_content", "")
                new_content = mod.get("new_content", "")
                operation = mod.get("operation", "replace")
                
                if 1 <= line_num <= len(lines):
                    if operation == "replace":
                        lines[line_num - 1] = new_content + '\n' if not new_content.endswith('\n') else new_content
                    elif operation == "insert":
                        lines.insert(line_num - 1, new_content + '\n' if not new_content.endswith('\n') else new_content)
                    elif operation == "delete":
                        if line_num <= len(lines):
                            del lines[line_num - 1]
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply modifications to {file_path}: {e}")
            return False
    
    def _format_plan_steps(self, steps: List[Dict[str, Any]]) -> str:
        """Format plan steps for AI context."""
        if not steps:
            return "No steps provided"
        
        formatted = []
        for i, step in enumerate(steps, 1):
            formatted.append(
                f"{i}. {step.get('action', 'Unknown action')}: "
                f"{step.get('description', 'No description')}\n"
                f"   Files: {', '.join(step.get('files', []))}"
            )
        
        return '\n'.join(formatted)
    
    def _format_file_contents(self, files: List[Dict[str, Any]]) -> str:
        """Format file contents for AI context."""
        if not files:
            return "No files available"
        
        formatted = []
        for file_info in files:
            formatted.append(
                f"File: {file_info['path']} ({file_info['lines']} lines)\n"
                f"```\n{file_info['content'][:1500]}\n```"  # Limit content
            )
        
        return '\n\n'.join(formatted)


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
    
    def __init__(self, ai_client: Optional[OpenAIClient] = None):
        self.ai_client = ai_client
    
    def get_state(self) -> AgentState:
        return AgentState.REPAIR
    
    async def execute(self, session: AgentSession) -> StepResult:
        """Analyze test failures and prepare for another iteration."""
        logger.info(f"Repairing - iteration {session.iteration_count + 1}")
        
        async with managed_operation("repair_analysis"):
            async with operation_timeout(session.config.state_timeout, "repair"):
                try:
                    # Check iteration limits
                    if session.iteration_count >= session.config.max_iterations:
                        logger.warning(f"Maximum iterations ({session.config.max_iterations}) reached. Escalating.")
                        return StepResult.ESCALATED
                    
                    # Get test results from previous TEST phase
                    test_results = session.context.get_code_context("test_results", {})
                    
                    # Analyze what went wrong and decide next steps
                    repair_decision = await self._analyze_test_failures(test_results, session)
                    
                    # Store repair analysis
                    session.context.add_code_context("repair_analysis", repair_decision)
                    
                    # Update session context with failure patterns
                    await self._update_failure_context(repair_decision, session)
                    
                    input_data = {
                        "iteration": session.iteration_count,
                        "max_iterations": session.config.max_iterations,
                        "test_failures": len(test_results.get("failing_tests", []))
                    }
                    
                    decision = repair_decision.get("decision", "escalate")
                    output_data = {
                        "decision": decision,
                        "confidence": repair_decision.get("confidence", 0.0),
                        "strategy_adjustment": repair_decision.get("strategy_adjustment", "none")
                    }
                    
                    if decision == "retry":
                        logger.info(f"Repair decision: RETRY with strategy adjustment")
                        return StepResult.RETRY
                    elif decision == "escalate":
                        logger.info(f"Repair decision: ESCALATE due to complexity or repeated failures")
                        return StepResult.ESCALATED
                    else:
                        logger.warning(f"Unknown repair decision: {decision}. Escalating.")
                        return StepResult.ESCALATED
                        
                except Exception as e:
                    logger.error(f"Error in repair handler: {e}")
                    # Default to retry unless we've hit max iterations
                    if session.iteration_count >= session.config.max_iterations:
                        return StepResult.ESCALATED
                    return StepResult.RETRY
    
    async def _analyze_test_failures(self, test_results: Dict[str, Any], session: AgentSession) -> Dict[str, Any]:
        """Analyze test failures to decide next steps."""
        if not self.ai_client:
            # Fallback logic without AI
            failing_tests = test_results.get("failing_tests", [])
            if len(failing_tests) == 0:
                return {"decision": "escalate", "reason": "No failing tests but repair called"}
            
            # Simple heuristic: retry if less than max iterations
            if session.iteration_count < session.config.max_iterations:
                return {
                    "decision": "retry",
                    "confidence": 0.5,
                    "strategy_adjustment": "basic_retry"
                }
            else:
                return {
                    "decision": "escalate", 
                    "confidence": 1.0,
                    "reason": "Max iterations reached"
                }
        
        # Get previous attempt context
        previous_plans = self._get_previous_attempts(session)
        current_failures = test_results.get("failing_tests", [])
        test_output = test_results.get("test_output", "")
        
        context = f"""
Repair Analysis - Iteration {session.iteration_count + 1}/{session.config.max_iterations}

Current Test Results:
- Exit Code: {test_results.get('exit_code', 'unknown')}
- Still Failing Tests: {len(current_failures)}
- New Test Output: {test_output[:1500]}

Previous Attempts Summary:
{self._format_previous_attempts(previous_plans)}

Current Failing Tests:
{self._format_failing_tests(current_failures)}

Repository Context: {session.repository.repo_path}
"""
        
        messages = [
            {
                "role": "user",
                "content": f"Analyze these test failures after applying patches. Decide whether to retry with a different approach or escalate to human review.\n\n{context}"
            }
        ]
        
        system_prompt = """You are a senior software engineer analyzing test failure patterns after attempted fixes.

Analyze the situation and decide:

1. **RETRY** if:
   - The fix was partially successful (fewer failing tests)  
   - You can identify a specific different approach
   - The failures suggest a simple oversight or missing step
   - There are still iterations remaining

2. **ESCALATE** if:
   - No progress was made (same or more failures)
   - The fix introduced new, unrelated failures
   - The problem appears more complex than initially assessed
   - The same fix strategy has failed multiple times

Provide:
- Clear decision (retry/escalate)  
- Confidence level (0.0-1.0)
- Reason for the decision
- Strategy adjustment if retrying"""
        
        # Create a simple schema for repair decisions
        repair_schema = {
            "type": "object",
            "required": ["decision", "confidence", "reason"],
            "properties": {
                "decision": {"type": "string", "enum": ["retry", "escalate"]},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reason": {"type": "string"},
                "strategy_adjustment": {"type": "string"},
                "new_approach": {"type": "string"},
            }
        }
        
        try:
            response = await self.ai_client.complete_with_schema(
                messages=messages,
                schema=repair_schema,
                system_prompt=system_prompt
            )
            
            if response.is_valid_json():
                logger.info(f"AI repair analysis completed. Cost: ${response.token_usage.estimated_cost:.4f}")
                return response.parsed_data
            else:
                logger.warning("AI repair analysis did not return valid JSON")
                return {
                    "decision": "retry" if session.iteration_count < session.config.max_iterations else "escalate",
                    "confidence": 0.3,
                    "reason": "AI analysis failed"
                }
                
        except AIClientError as e:
            logger.error(f"AI repair analysis failed: {e}")
            return {
                "decision": "retry" if session.iteration_count < session.config.max_iterations else "escalate", 
                "confidence": 0.2,
                "reason": f"AI analysis error: {e}"
            }
    
    async def _update_failure_context(self, repair_decision: Dict[str, Any], session: AgentSession) -> None:
        """Update session context with failure patterns and learning."""
        # Track failure patterns across iterations
        failure_history = session.context.get_code_context("failure_history", [])
        
        current_iteration_info = {
            "iteration": session.iteration_count,
            "decision": repair_decision.get("decision"),
            "reason": repair_decision.get("reason"), 
            "strategy_adjustment": repair_decision.get("strategy_adjustment"),
            "timestamp": time.time()
        }
        
        failure_history.append(current_iteration_info)
        session.context.add_code_context("failure_history", failure_history)
        
        # Update strategy context if we're retrying
        if repair_decision.get("decision") == "retry":
            strategy_context = session.context.get_code_context("strategy_context", {})
            strategy_context["current_approach"] = repair_decision.get("new_approach", "adjusted")
            strategy_context["failed_approaches"] = strategy_context.get("failed_approaches", [])
            
            # Track what didn't work
            if session.iteration_count > 0:
                last_plan = session.context.get_code_context("plan_data", {})
                if last_plan:
                    strategy_context["failed_approaches"].append({
                        "iteration": session.iteration_count,
                        "strategy": last_plan.get("strategy", "unknown"),
                        "reason_failed": repair_decision.get("reason", "unknown")
                    })
            
            session.context.add_code_context("strategy_context", strategy_context)
    
    def _get_previous_attempts(self, session: AgentSession) -> List[Dict[str, Any]]:
        """Get summaries of previous repair attempts."""
        failure_history = session.context.get_code_context("failure_history", [])
        return failure_history
    
    def _format_previous_attempts(self, attempts: List[Dict[str, Any]]) -> str:
        """Format previous attempts for AI context."""
        if not attempts:
            return "No previous attempts"
        
        formatted = []
        for attempt in attempts:
            formatted.append(
                f"Iteration {attempt.get('iteration', '?')}: "
                f"{attempt.get('decision', 'unknown')} - {attempt.get('reason', 'no reason')}"
            )
        
        return '\n'.join(formatted)
    
    def _format_failing_tests(self, failing_tests: List[str]) -> str:
        """Format failing tests for AI context."""
        if not failing_tests:
            return "No failing tests"
        
        # Show first few failing tests
        formatted = failing_tests[:5]
        if len(failing_tests) > 5:
            formatted.append(f"... and {len(failing_tests) - 5} more")
        
        return '\n'.join([f"- {test}" for test in formatted])


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
            AgentState.PLAN: PlanHandler(ai_client),
            AgentState.PATCH: PatchHandler(ai_client),
            AgentState.TEST: TestHandler(),
            AgentState.REPAIR: RepairHandler(ai_client),
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