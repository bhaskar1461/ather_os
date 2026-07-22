"""
Type definitions for the Prompt Orchestration Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    GENERAL = "general"
    CODING = "coding"
    WRITING = "writing"
    REASONING = "reasoning"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    TEACHING = "teaching"
    REVIEW = "review"
    PLANNING = "planning"


class PromptRole(str, Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class PromptModule:
    """
    A single versioned prompt component loaded from a markdown file.
    """
    name: str
    content: str
    version: int = 1
    priority: int = 0  # Higher = injected earlier in the prompt
    token_estimate: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Rough token estimate: ~4 chars per token for English
        if self.token_estimate == 0:
            self.token_estimate = max(1, len(self.content) // 4)


@dataclass
class MemoryItem:
    """A retrieved memory for injection into the prompt context."""
    key: str
    value: str
    relevance_score: float = 1.0
    source_chat_id: str | None = None


@dataclass
class DocumentChunk:
    """A retrieved document chunk for RAG injection."""
    content: str
    source: str
    page: int | None = None
    relevance_score: float = 1.0
    citation_id: str = ""


@dataclass
class ConversationSummary:
    """Compressed representation of older conversation turns."""
    summary: str
    message_count: int
    token_count: int


@dataclass
class ToolDefinition:
    """A tool the AI model can invoke."""
    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """Configuration for the target AI provider."""
    provider_name: str  # e.g. 'kimi', 'bedrock', 'openai', 'anthropic'
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class CompiledPrompt:
    """
    The final output of the PromptBuilder — a fully assembled prompt
    ready to be sent to an AI provider.
    """
    messages: list[dict[str, str]]
    provider_config: ProviderConfig
    total_tokens_estimate: int = 0
    debug_info: dict[str, Any] = field(default_factory=dict)

    def to_provider_format(self) -> dict[str, Any]:
        """Serialize to the format expected by the provider SDK."""
        return {
            "messages": self.messages,
            "model": self.provider_config.model_id,
            "max_tokens": self.provider_config.max_tokens,
            "temperature": self.provider_config.temperature,
            "top_p": self.provider_config.top_p,
            "stop": self.provider_config.stop_sequences or None,
        }


@dataclass
class PromptDebugData:
    """
    Complete debug snapshot of the prompt compilation process.
    Used by the Prompt Debugger UI.
    """
    task_type: str
    modules_used: list[str]
    module_versions: dict[str, int]
    system_prompt: str
    developer_prompt: str
    user_prompt: str
    injected_memories: list[dict[str, Any]]
    injected_documents: list[dict[str, Any]]
    conversation_summary: str | None
    recent_messages: list[dict[str, str]]
    tools: list[dict[str, Any]]
    provider_formatting: str
    total_token_estimate: int
    context_window_usage_percent: float
    estimated_cost_usd: float
    compilation_time_ms: float
