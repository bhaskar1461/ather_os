"""
Prompt Module Registry

Central registry that tracks all available prompt modules, their versions,
and allows hot-reloading without application restart.
"""

from pathlib import Path
from typing import Any

from app.prompt_engine.types import PromptModule
from app.prompt_engine.loader import load_module, load_all_modules, list_versions

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class PromptRegistry:
    """
    Singleton-style registry for prompt modules.
    Caches loaded modules and supports version switching at runtime.
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._cache: dict[str, PromptModule] = {}
        self._version_overrides: dict[str, int] = {}

    def load_all(self) -> None:
        """Load all prompt modules from the prompts directory into cache."""
        self._cache = load_all_modules(self._prompts_dir)

    def get(self, name: str) -> PromptModule:
        """
        Get a prompt module by name.
        Respects version overrides. Falls back to cache, then disk.
        """
        override_version = self._version_overrides.get(name)

        if override_version is not None:
            return load_module(name, version=override_version, prompts_dir=self._prompts_dir)

        if name in self._cache:
            return self._cache[name]

        module = load_module(name, prompts_dir=self._prompts_dir)
        self._cache[name] = module
        return module

    def set_version(self, name: str, version: int) -> None:
        """Override the version used for a specific module."""
        self._version_overrides[name] = version

    def clear_version_override(self, name: str) -> None:
        """Remove a version override, reverting to the latest."""
        self._version_overrides.pop(name, None)

    def get_versions(self, name: str) -> list[int]:
        """List all available versions for a module."""
        return list_versions(name, self._prompts_dir)

    def reload(self, name: str | None = None) -> None:
        """
        Reload a specific module or all modules from disk.
        Useful for hot-reloading prompt changes without restart.
        """
        if name:
            self._cache.pop(name, None)
            try:
                self._cache[name] = load_module(name, prompts_dir=self._prompts_dir)
            except FileNotFoundError:
                pass
        else:
            self._cache.clear()
            self.load_all()

    def list_modules(self) -> list[dict[str, Any]]:
        """Return metadata for all loaded modules."""
        return [
            {
                "name": m.name,
                "version": m.version,
                "priority": m.priority,
                "token_estimate": m.token_estimate,
                "tags": m.tags,
            }
            for m in self._cache.values()
        ]

    @property
    def module_count(self) -> int:
        return len(self._cache)


# Global registry instance
registry = PromptRegistry()
