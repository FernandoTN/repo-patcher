"""OpenAI API client with structured outputs and cost tracking."""
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from jsonschema import validate, ValidationError
import openai
from openai import AsyncOpenAI

from .config import AgentConfig
from .exceptions import AIClientError, ConfigurationError
import logging


@dataclass
class TokenUsage:
    """Token usage tracking for cost calculation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @property
    def estimated_cost(self) -> float:
        """Estimate cost based on gpt-4o-mini pricing."""
        # gpt-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens
        input_cost = (self.prompt_tokens / 1_000_000) * 0.15
        output_cost = (self.completion_tokens / 1_000_000) * 0.60
        return input_cost + output_cost


@dataclass
class AIResponse:
    """Structured AI response with validation."""
    content: str
    parsed_data: Optional[Dict[str, Any]] = None
    token_usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    
    def is_valid_json(self) -> bool:
        """Check if response is valid JSON."""
        return self.parsed_data is not None


class OpenAIClient:
    """OpenAI API client with retry logic, structured outputs, and cost tracking."""
    
    def __init__(self, config: AgentConfig):
        """Initialize OpenAI client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not config.openai_api_key:
            raise ConfigurationError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
            )
        
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        
        self.total_cost = 0.0
        self.total_tokens = TokenUsage()
    
    async def complete_with_schema(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> AIResponse:
        """
        Complete with JSON schema validation.
        
        Args:
            messages: Conversation messages
            schema: JSON schema for response validation
            system_prompt: Optional system prompt to prepend
            max_retries: Override default retry attempts
            
        Returns:
            AIResponse with validated structured data
            
        Raises:
            AIClientError: On API or validation failures
        """
        max_retries = max_retries or self.config.retry_attempts
        
        # Prepare messages
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages.copy()
        
        # Add JSON format instruction
        full_messages.append({
            "role": "system", 
            "content": f"Respond with valid JSON matching this schema: {json.dumps(schema)}"
        })
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"API request attempt {attempt + 1}/{max_retries + 1}")
                
                response = await self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=full_messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                
                # Extract response data
                content = response.choices[0].message.content or ""
                finish_reason = response.choices[0].finish_reason
                
                # Track token usage
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0,
                )
                
                self.total_tokens.prompt_tokens += usage.prompt_tokens
                self.total_tokens.completion_tokens += usage.completion_tokens
                self.total_tokens.total_tokens += usage.total_tokens
                self.total_cost += usage.estimated_cost
                
                self.logger.info(f"API call completed. Tokens: {usage.total_tokens}, Cost: ${usage.estimated_cost:.4f}")
                
                # Parse and validate JSON
                try:
                    parsed_data = json.loads(content)
                    validate(instance=parsed_data, schema=schema)
                    
                    return AIResponse(
                        content=content,
                        parsed_data=parsed_data,
                        token_usage=usage,
                        model=self.config.model_name,
                        finish_reason=finish_reason,
                    )
                    
                except (json.JSONDecodeError, ValidationError) as e:
                    if attempt < max_retries:
                        self.logger.warning(f"JSON validation failed (attempt {attempt + 1}): {e}")
                        full_messages.append({
                            "role": "assistant", 
                            "content": content
                        })
                        full_messages.append({
                            "role": "user",
                            "content": f"Invalid JSON response. Error: {str(e)}. Please provide valid JSON matching the schema."
                        })
                        continue
                    else:
                        raise AIClientError(f"Failed to get valid JSON after {max_retries + 1} attempts: {e}")
                
            except openai.APIError as e:
                if attempt < max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"API error (attempt {attempt + 1}): {e}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise AIClientError(f"OpenAI API error after {max_retries + 1} attempts: {e}")
            
            except Exception as e:
                raise AIClientError(f"Unexpected error: {e}")
        
        raise AIClientError(f"Failed after {max_retries + 1} attempts")
    
    async def simple_complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """
        Simple completion without structured output.
        
        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt to prepend
            
        Returns:
            AIResponse with text content
        """
        # Prepare messages
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages.copy()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=full_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            # Extract response data
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            # Track token usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )
            
            self.total_tokens.prompt_tokens += usage.prompt_tokens
            self.total_tokens.completion_tokens += usage.completion_tokens
            self.total_tokens.total_tokens += usage.total_tokens
            self.total_cost += usage.estimated_cost
            
            self.logger.info(f"API call completed. Tokens: {usage.total_tokens}, Cost: ${usage.estimated_cost:.4f}")
            
            return AIResponse(
                content=content,
                token_usage=usage,
                model=self.config.model_name,
                finish_reason=finish_reason,
            )
            
        except openai.APIError as e:
            raise AIClientError(f"OpenAI API error: {e}")
        except Exception as e:
            raise AIClientError(f"Unexpected error: {e}")
    
    def get_total_cost(self) -> float:
        """Get total session cost."""
        return self.total_cost
    
    def get_total_usage(self) -> TokenUsage:
        """Get total token usage."""
        return self.total_tokens
    
    def reset_usage(self):
        """Reset usage tracking."""
        self.total_cost = 0.0
        self.total_tokens = TokenUsage()
    
    def check_cost_limit(self) -> bool:
        """Check if cost limit exceeded."""
        return self.total_cost >= self.config.max_cost_per_session
    
    def check_cost_warning(self) -> bool:
        """Check if cost warning threshold reached."""
        return self.total_cost >= self.config.cost_warning_threshold


# JSON Schemas for structured outputs
INGEST_SCHEMA = {
    "type": "object",
    "required": ["failing_tests", "analysis", "code_context"],
    "properties": {
        "failing_tests": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["test_name", "error_type", "error_message"],
                "properties": {
                    "test_name": {"type": "string"},
                    "error_type": {"type": "string"},
                    "error_message": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line_number": {"type": ["integer", "null"]},
                }
            }
        },
        "analysis": {
            "type": "object",
            "required": ["root_cause", "affected_files", "complexity_level"],
            "properties": {
                "root_cause": {"type": "string"},
                "affected_files": {"type": "array", "items": {"type": "string"}},
                "complexity_level": {"type": "string", "enum": ["simple", "medium", "complex"]},
                "dependencies": {"type": "array", "items": {"type": "string"}},
            }
        },
        "code_context": {
            "type": "object",
            "properties": {
                "imports": {"type": "array", "items": {"type": "string"}},
                "functions": {"type": "array", "items": {"type": "string"}},
                "classes": {"type": "array", "items": {"type": "string"}},
            }
        }
    }
}

PLAN_SCHEMA = {
    "type": "object",
    "required": ["strategy", "steps", "risk_assessment"],
    "properties": {
        "strategy": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action", "description", "files"],
                "properties": {
                    "action": {"type": "string"},
                    "description": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "expected_outcome": {"type": "string"},
                }
            }
        },
        "risk_assessment": {
            "type": "object",
            "required": ["risk_level", "confidence"],
            "properties": {
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "potential_issues": {"type": "array", "items": {"type": "string"}},
            }
        }
    }
}

PATCH_SCHEMA = {
    "type": "object",
    "required": ["changes"],
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["file_path", "modifications"],
                "properties": {
                    "file_path": {"type": "string"},
                    "modifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["line_number", "old_content", "new_content"],
                            "properties": {
                                "line_number": {"type": "integer"},
                                "old_content": {"type": "string"},
                                "new_content": {"type": "string"},
                                "operation": {"type": "string", "enum": ["replace", "insert", "delete"]},
                            }
                        }
                    }
                }
            }
        },
        "explanation": {"type": "string"},
        "diff_summary": {
            "type": "object",
            "properties": {
                "files_modified": {"type": "integer"},
                "lines_added": {"type": "integer"},
                "lines_removed": {"type": "integer"},
            }
        }
    }
}