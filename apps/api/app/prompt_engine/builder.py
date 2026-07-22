"""
Prompt Composition Engine

Dynamically assembles a final prompt from modular components.
Supports task-specific module selection, memory/document injection,
conversation compression, and provider-specific formatting.

Usage:
    prompt = (
        PromptBuilder(provider_config)
        .set_task(TaskType.CODING)
        .add_module("core_identity")
        .add_module("behavior")
        .add_module("coding")
        .inject_memories(relevant_memories)
        .inject_documents(relevant_chunks)
        .set_conversation(summary, recent_messages)
        .add_tools(tool_definitions)
        .add_module("formatting")
        .set_user_message(user_input)
        .compile()
    )
"""

import time
from typing import Any

from app.prompt_engine.types import (
    CompiledPrompt,
    ConversationSummary,
    DocumentChunk,
    MemoryItem,
    PromptDebugData,
    PromptModule,
    PromptRole,
    ProviderConfig,
    TaskType,
    ToolDefinition,
)
from app.prompt_engine.loader import load_module
from app.prompt_engine.optimizer import optimize_prompt_content


# Default module map: which modules to auto-include per task type
_TASK_MODULE_MAP: dict[TaskType, list[str]] = {
    TaskType.GENERAL: ["core_identity", "behavior", "assistant", "formatting"],
    TaskType.CODING: ["core_identity", "behavior", "coding", "formatting"],
    TaskType.WRITING: ["core_identity", "behavior", "writing", "formatting"],
    TaskType.REASONING: ["core_identity", "behavior", "reasoning", "formatting"],
    TaskType.RESEARCH: ["core_identity", "behavior", "research", "formatting"],
    TaskType.ANALYSIS: ["core_identity", "behavior", "analysis", "formatting"],
    TaskType.DEBUGGING: ["core_identity", "behavior", "debugger", "formatting"],
    TaskType.ARCHITECTURE: ["core_identity", "behavior", "architect", "formatting"],
    TaskType.TEACHING: ["core_identity", "behavior", "teacher", "formatting"],
    TaskType.REVIEW: ["core_identity", "behavior", "reviewer", "formatting"],
    TaskType.PLANNING: ["core_identity", "behavior", "planner", "formatting"],
}


class PromptBuilder:
    """
    Fluent builder that composes prompt modules into a compiled prompt.
    """

    def __init__(self, provider_config: ProviderConfig) -> None:
        self._provider_config = provider_config
        self._task_type: TaskType = TaskType.GENERAL
        self._modules: list[PromptModule] = []
        self._memories: list[MemoryItem] = []
        self._documents: list[DocumentChunk] = []
        self._conversation_summary: ConversationSummary | None = None
        self._recent_messages: list[dict[str, str]] = []
        self._tools: list[ToolDefinition] = []
        self._user_message: str = ""
        self._developer_instructions: str = ""
        self._debug_mode: bool = False
        self._start_time: float = 0.0

    def set_task(self, task_type: TaskType) -> "PromptBuilder":
        """Set the task type for automatic module selection."""
        self._task_type = task_type
        return self

    def add_module(self, name: str, version: int | None = None) -> "PromptBuilder":
        """Load and add a prompt module by name."""
        module = load_module(name, version=version)
        self._modules.append(module)
        return self

    def add_module_direct(self, module: PromptModule) -> "PromptBuilder":
        """Add a pre-loaded prompt module."""
        self._modules.append(module)
        return self

    def auto_select_modules(self) -> "PromptBuilder":
        """
        Automatically load modules based on the current task type.
        Uses the _TASK_MODULE_MAP to determine which modules to include.
        """
        module_names = _TASK_MODULE_MAP.get(self._task_type, _TASK_MODULE_MAP[TaskType.GENERAL])
        for name in module_names:
            try:
                self.add_module(name)
            except FileNotFoundError:
                # Module not yet created — skip gracefully
                pass
        return self

    def inject_memories(self, memories: list[MemoryItem], max_items: int = 10) -> "PromptBuilder":
        """
        Inject relevant memories sorted by relevance score.
        Only the top N memories are included to conserve context.
        """
        sorted_memories = sorted(memories, key=lambda m: m.relevance_score, reverse=True)
        self._memories = sorted_memories[:max_items]
        return self

    def inject_documents(self, chunks: list[DocumentChunk], max_chunks: int = 5) -> "PromptBuilder":
        """
        Inject relevant document chunks sorted by relevance.
        Deduplicates chunks with identical content.
        """
        seen_content: set[str] = set()
        unique_chunks: list[DocumentChunk] = []
        for chunk in sorted(chunks, key=lambda c: c.relevance_score, reverse=True):
            content_hash = chunk.content[:200]
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_chunks.append(chunk)
        self._documents = unique_chunks[:max_chunks]
        return self

    def set_conversation(
        self,
        summary: ConversationSummary | None,
        recent_messages: list[dict[str, str]],
    ) -> "PromptBuilder":
        """
        Set conversation context.
        Older messages are provided as a summary; recent ones are kept verbatim.
        """
        self._conversation_summary = summary
        self._recent_messages = recent_messages
        return self

    def add_tools(self, tools: list[ToolDefinition]) -> "PromptBuilder":
        """Register tool definitions for function calling."""
        self._tools = tools
        return self

    def set_user_message(self, message: str) -> "PromptBuilder":
        """Set the user's current message."""
        self._user_message = message
        return self

    def set_developer_instructions(self, instructions: str) -> "PromptBuilder":
        """Set developer-level instructions (hidden from the user in UI)."""
        self._developer_instructions = instructions
        return self

    def enable_debug(self) -> "PromptBuilder":
        """Enable debug data collection during compilation."""
        self._debug_mode = True
        self._start_time = time.perf_counter()
        return self

    def compile(self) -> CompiledPrompt:
        """
        Assemble all components into a final CompiledPrompt.

        Assembly order:
        1. System prompt (composed from modules)
        2. Developer instructions
        3. Memory context
        4. Document context
        5. Conversation summary
        6. Recent messages (verbatim)
        7. Current user message
        """
        if self._debug_mode and self._start_time == 0.0:
            self._start_time = time.perf_counter()

        # Automatically load provider-specific prompt module based on model_id
        if self._provider_config.model_id:
            provider_module_name = None
            if self._provider_config.model_id.startswith("moonshotai.kimi-"):
                provider_module_name = "provider/kimi"
            elif self._provider_config.model_id.startswith("deepseek."):
                provider_module_name = "provider/deepseek"
            
            if provider_module_name:
                try:
                    # Only add if it's not already added
                    if not any(m.name == provider_module_name for m in self._modules):
                        self.add_module(provider_module_name)
                except FileNotFoundError:
                    pass

        messages: list[dict[str, str]] = []

        # ── 1. System Prompt Assembly ─────────────────────────────────────
        sorted_modules = sorted(self._modules, key=lambda m: m.priority, reverse=True)
        system_parts: list[str] = [m.content for m in sorted_modules if m.content.strip()]
        system_prompt = optimize_prompt_content("\n\n".join(system_parts))

        if system_prompt:
            messages.append({"role": PromptRole.SYSTEM.value, "content": system_prompt})

        # ── 2. Developer Instructions ─────────────────────────────────────
        developer_prompt = ""
        if self._developer_instructions:
            developer_prompt = self._developer_instructions
            messages.append({"role": PromptRole.SYSTEM.value, "content": f"[Developer Instructions]\n{developer_prompt}"})

        # ── 3. Memory Context ─────────────────────────────────────────────
        if self._memories:
            memory_lines = ["[Relevant Memories]"]
            for mem in self._memories:
                memory_lines.append(f"- {mem.key}: {mem.value}")
            messages.append({
                "role": PromptRole.SYSTEM.value,
                "content": "\n".join(memory_lines),
            })

        # ── 4. Document Context (RAG) ─────────────────────────────────────
        if self._documents:
            doc_lines = ["[Retrieved Documents]"]
            for i, doc in enumerate(self._documents, 1):
                source_info = f"Source: {doc.source}"
                if doc.page is not None:
                    source_info += f", Page {doc.page}"
                doc_lines.append(f"\n[Document {i}] ({source_info})\n{doc.content}")
            messages.append({
                "role": PromptRole.SYSTEM.value,
                "content": "\n".join(doc_lines),
            })

        # ── 5. Conversation Summary ───────────────────────────────────────
        if self._conversation_summary:
            messages.append({
                "role": PromptRole.SYSTEM.value,
                "content": f"[Conversation Summary — {self._conversation_summary.message_count} previous messages]\n{self._conversation_summary.summary}",
            })

        # ── 6. Recent Messages (verbatim) ─────────────────────────────────
        for msg in self._recent_messages:
            messages.append(msg)

        # ── 7. Current User Message ───────────────────────────────────────
        if self._user_message:
            messages.append({"role": PromptRole.USER.value, "content": self._user_message})

        # ── Token Estimation ──────────────────────────────────────────────
        total_chars = sum(len(m["content"]) for m in messages)
        total_tokens_estimate = total_chars // 4

        # ── Debug Info ────────────────────────────────────────────────────
        debug_info: dict[str, Any] = {}
        if self._debug_mode:
            compilation_ms = (time.perf_counter() - self._start_time) * 1000
            context_window = self._provider_config.max_tokens * 4  # rough context estimate
            debug_info = PromptDebugData(
                task_type=self._task_type.value,
                modules_used=[m.name for m in sorted_modules],
                module_versions={m.name: m.version for m in sorted_modules},
                system_prompt=system_prompt,
                developer_prompt=developer_prompt,
                user_prompt=self._user_message,
                injected_memories=[
                    {"key": m.key, "value": m.value, "score": m.relevance_score}
                    for m in self._memories
                ],
                injected_documents=[
                    {"source": d.source, "score": d.relevance_score, "preview": d.content[:100]}
                    for d in self._documents
                ],
                conversation_summary=self._conversation_summary.summary if self._conversation_summary else None,
                recent_messages=self._recent_messages,
                tools=[{"name": t.name, "description": t.description} for t in self._tools],
                provider_formatting=self._provider_config.provider_name,
                total_token_estimate=total_tokens_estimate,
                context_window_usage_percent=round((total_tokens_estimate / max(context_window, 1)) * 100, 2),
                estimated_cost_usd=0.0,  # Provider-specific cost calculation
                compilation_time_ms=round(compilation_ms, 3),
            ).__dict__

        return CompiledPrompt(
            messages=messages,
            provider_config=self._provider_config,
            total_tokens_estimate=total_tokens_estimate,
            debug_info=debug_info,
        )
