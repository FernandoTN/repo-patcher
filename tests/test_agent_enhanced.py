"""Enhanced tests for agent components."""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_patcher.agent.config import AgentConfig
from repo_patcher.agent.context import SessionContext, CodeContext, ConversationContext
from repo_patcher.agent.exceptions import CostLimitExceededError, SafetyViolationError
from repo_patcher.agent.models import AgentSession, RepositoryContext, AgentState
from repo_patcher.agent.logging_config import setup_logging, get_agent_logger


class TestAgentConfig:
    """Test agent configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig()
        
        assert config.max_iterations == 3
        assert config.max_cost_per_session == 5.0
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.1
        assert len(config.blocked_paths) > 0
        assert len(config.allowed_file_types) > 0
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = AgentConfig()
        assert config.validate() == True
        
        # Test invalid values
        config.max_iterations = 0
        with pytest.raises(ValueError):
            config.validate()
        
        config.max_iterations = 3
        config.temperature = 1.5
        with pytest.raises(ValueError):
            config.validate()
    
    def test_config_from_env(self, monkeypatch):
        """Test loading config from environment."""
        monkeypatch.setenv("AGENT_MAX_ITERATIONS", "5")
        monkeypatch.setenv("AGENT_MAX_COST", "10.0")
        monkeypatch.setenv("AGENT_MODEL", "gpt-3.5-turbo")
        
        config = AgentConfig.from_env()
        
        assert config.max_iterations == 5
        assert config.max_cost_per_session == 10.0
        assert config.model_name == "gpt-3.5-turbo"


class TestSessionContext:
    """Test session context management."""
    
    def test_context_creation(self):
        """Test creating session context."""
        context = SessionContext()
        
        assert isinstance(context.code, CodeContext)
        assert isinstance(context.conversation, ConversationContext)
        assert isinstance(context.metadata, dict)
    
    def test_conversation_context(self):
        """Test conversation context management."""
        conv = ConversationContext()
        conv.system_prompt = "You are a helpful assistant"
        
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")
        
        assert len(conv.messages) == 2
        assert conv.messages[0]["role"] == "user"
        assert conv.messages[1]["content"] == "Hi there!"
        
        recent = conv.get_recent_messages(1)
        assert len(recent) == 1
        assert recent[0]["role"] == "assistant"
    
    def test_context_persistence(self):
        """Test saving and loading context."""
        context = SessionContext()
        context.code.file_structure = {"src/": ["main.py", "utils.py"]}
        context.conversation.add_message("user", "Fix this test")
        context.metadata["test_framework"] = "pytest"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            context_file = Path(temp_dir) / "context.json"
            
            # Save context
            context.save_to_file(context_file)
            assert context_file.exists()
            
            # Load context
            loaded = SessionContext.load_from_file(context_file)
            assert loaded.code.file_structure == context.code.file_structure
            assert len(loaded.conversation.messages) == 1
            assert loaded.metadata["test_framework"] == "pytest"


class TestEnhancedAgentSession:
    """Test enhanced agent session functionality."""
    
    def test_session_with_config(self):
        """Test session with custom configuration."""
        config = AgentConfig(max_iterations=5, max_cost_per_session=10.0)
        
        repo = RepositoryContext(
            repo_path=Path("/tmp/test"),
            repo_url="https://github.com/test/repo",
            branch="main",
            commit_sha="abc123",
            test_framework="pytest",
            test_command="pytest"
        )
        
        session = AgentSession(
            session_id="test-123",
            repository=repo,
            current_state=AgentState.INGEST,
            config=config
        )
        
        assert session.max_iterations == 5
        assert session.config.max_cost_per_session == 10.0
        assert isinstance(session.context, SessionContext)
    
    def test_cost_and_time_limits(self):
        """Test cost and time limit checking."""
        config = AgentConfig(max_cost_per_session=1.0, max_session_duration=60)
        repo = RepositoryContext(
            repo_path=Path("/tmp/test"),
            repo_url="",
            branch="main", 
            commit_sha="",
            test_framework="pytest",
            test_command="pytest"
        )
        
        session = AgentSession(
            session_id="test-123",
            repository=repo,
            current_state=AgentState.INGEST,
            config=config
        )
        
        # Test cost limit
        session.total_cost = 0.5
        assert not session.check_cost_limit()
        assert session.is_safe_to_continue()
        
        session.total_cost = 1.5
        assert session.check_cost_limit()
        assert not session.is_safe_to_continue()
    
    def test_session_summary(self):
        """Test session summary generation."""
        repo = RepositoryContext(
            repo_path=Path("/tmp/test"),
            repo_url="",
            branch="main",
            commit_sha="",
            test_framework="pytest", 
            test_command="pytest"
        )
        
        session = AgentSession(
            session_id="test-123",
            repository=repo,
            current_state=AgentState.PLAN
        )
        
        session.total_cost = 2.5
        session.iteration_count = 2
        
        summary = session.get_session_summary()
        
        assert summary["session_id"] == "test-123"
        assert summary["state"] == "plan"
        assert summary["iterations"] == 2
        assert summary["cost"] == 2.5
        assert summary["complete"] == False


class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_logger_setup(self):
        """Test setting up logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "agent.log"
            
            setup_logging(
                level="DEBUG",
                log_file=log_file,
                structured=False,
                session_id="test-session"
            )
            
            logger = get_agent_logger("test")
            logger.info("Test message")
            
            # Check that log file was created
            assert log_file.exists()
            
            # Check log contents
            log_content = log_file.read_text()
            assert "Test message" in log_content
    
    def test_structured_logging(self):
        """Test structured JSON logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "structured.log" 
            
            setup_logging(
                level="INFO",
                log_file=log_file,
                structured=True
            )
            
            logger = get_agent_logger("structured_test")
            logger.info("Structured log message")
            
            log_content = log_file.read_text()
            assert "Structured log message" in log_content
            # Should contain JSON structure
            assert '"level": "INFO"' in log_content