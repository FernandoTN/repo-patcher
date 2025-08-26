"""Context management for agent sessions."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import json


@dataclass
class CodeContext:
    """Context about the codebase being analyzed."""
    file_structure: Dict[str, Any] = field(default_factory=dict)
    imports_map: Dict[str, List[str]] = field(default_factory=dict)
    function_signatures: Dict[str, Dict] = field(default_factory=dict)
    class_hierarchy: Dict[str, List[str]] = field(default_factory=dict)
    test_patterns: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass 
class ConversationContext:
    """Context for AI conversations."""
    messages: List[Dict[str, str]] = field(default_factory=list)
    system_prompt: str = ""
    previous_attempts: List[Dict] = field(default_factory=list)
    learned_patterns: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append({"role": role, "content": content})
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        return self.messages[-count:]
    
    def clear_messages(self, keep_system: bool = True) -> None:
        """Clear conversation messages."""
        if keep_system and self.messages and self.messages[0]["role"] == "system":
            system_msg = self.messages[0]
            self.messages = [system_msg]
        else:
            self.messages = []


@dataclass
class SessionContext:
    """Complete context for an agent session."""
    code: CodeContext = field(default_factory=CodeContext)
    conversation: ConversationContext = field(default_factory=ConversationContext)
    metadata: Dict[str, Any] = field(default_factory=dict)
    code_context: Dict[str, Any] = field(default_factory=dict)  # Additional code context storage
    
    def add_code_context(self, key: str, value: Any) -> None:
        """Add code context information."""
        self.code_context[key] = value
    
    def save_to_file(self, path: Path) -> None:
        """Save context to JSON file."""
        data = {
            "code": {
                "file_structure": self.code.file_structure,
                "imports_map": self.code.imports_map,
                "function_signatures": self.code.function_signatures,
                "class_hierarchy": self.code.class_hierarchy,
                "test_patterns": self.code.test_patterns,
                "dependencies": self.code.dependencies,
            },
            "conversation": {
                "messages": self.conversation.messages,
                "system_prompt": self.conversation.system_prompt,
                "previous_attempts": self.conversation.previous_attempts,
                "learned_patterns": self.conversation.learned_patterns,
            },
            "metadata": self.metadata
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load_from_file(cls, path: Path) -> "SessionContext":
        """Load context from JSON file."""
        if not path.exists():
            return cls()
        
        with open(path) as f:
            data = json.load(f)
        
        context = cls()
        
        # Load code context
        code_data = data.get("code", {})
        context.code = CodeContext(
            file_structure=code_data.get("file_structure", {}),
            imports_map=code_data.get("imports_map", {}),
            function_signatures=code_data.get("function_signatures", {}),
            class_hierarchy=code_data.get("class_hierarchy", {}),
            test_patterns=code_data.get("test_patterns", []),
            dependencies=code_data.get("dependencies", [])
        )
        
        # Load conversation context
        conv_data = data.get("conversation", {})
        context.conversation = ConversationContext(
            messages=conv_data.get("messages", []),
            system_prompt=conv_data.get("system_prompt", ""),
            previous_attempts=conv_data.get("previous_attempts", []),
            learned_patterns=conv_data.get("learned_patterns", {})
        )
        
        context.metadata = data.get("metadata", {})
        
        return context