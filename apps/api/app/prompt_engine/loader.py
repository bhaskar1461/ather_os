"""
Prompt Module Loader

Loads prompt modules from versioned markdown files on disk.
Supports directory-based versioning (v1/, v2/) and front-matter metadata parsing.

Directory structure:
    prompts/
        core_identity.md          ← current version (latest)
        behavior.md
        coding.md
        versions/
            core_identity/
                v1.md
                v2.md
            coding/
                v1.md
        provider/
            deepseek.md
"""

import os
import re
from pathlib import Path
from typing import Any

from app.prompt_engine.types import PromptModule

# Default prompts directory relative to the api app
_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _parse_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML-like front matter delimited by --- from a markdown file.
    Returns (metadata_dict, body_content).
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(raw)
    if not match:
        return {}, raw.strip()

    front_matter_text = match.group(1)
    body = raw[match.end():].strip()

    metadata: dict[str, Any] = {}
    for line in front_matter_text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Parse simple types
            if value.lower() in ("true", "false"):
                metadata[key] = value.lower() == "true"
            elif value.isdigit():
                metadata[key] = int(value)
            elif value.startswith("[") and value.endswith("]"):
                # Simple list parsing: [tag1, tag2]
                items = [item.strip().strip("'\"") for item in value[1:-1].split(",")]
                metadata[key] = [i for i in items if i]
            else:
                metadata[key] = value.strip("'\"")

    return metadata, body


from functools import lru_cache

@lru_cache(maxsize=128)
def _read_file_cached(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


def load_module(name: str, version: int | None = None, prompts_dir: Path | None = None) -> PromptModule:
    """
    Load a single prompt module by name.

    Args:
        name: Module name (e.g., 'core_identity', 'provider/deepseek').
        version: Specific version to load. None loads the latest (top-level file).
        prompts_dir: Override the prompts directory path.

    Returns:
        PromptModule with parsed content and metadata.

    Raises:
        FileNotFoundError: If the prompt module file does not exist.
    """
    base_dir = prompts_dir or _PROMPTS_DIR

    if version is not None:
        # Load from versions/<name>/v<N>.md
        clean_name = name.replace("/", os.sep)
        file_path = base_dir / "versions" / clean_name / f"v{version}.md"
    else:
        # Load the current/latest version
        file_path = base_dir / f"{name}.md"

    if not file_path.exists():
        raise FileNotFoundError(f"Prompt module not found: {file_path}")

    raw_content = _read_file_cached(str(file_path))
    metadata, body = _parse_front_matter(raw_content)

    return PromptModule(
        name=name,
        content=body,
        version=metadata.get("version", 1),
        priority=metadata.get("priority", 0),
        tags=metadata.get("tags", []),
        metadata=metadata,
    )


def load_all_modules(prompts_dir: Path | None = None) -> dict[str, PromptModule]:
    """
    Scan the prompts directory and load all top-level .md files as modules.

    Returns:
        Dictionary mapping module name to PromptModule.
    """
    base_dir = prompts_dir or _PROMPTS_DIR
    modules: dict[str, PromptModule] = {}

    if not base_dir.exists():
        return modules

    for md_file in base_dir.rglob("*.md"):
        # Skip versioned files
        relative = md_file.relative_to(base_dir)
        parts = relative.parts
        if "versions" in parts:
            continue

        # Derive module name from path
        module_name = str(relative.with_suffix("")).replace(os.sep, "/")
        try:
            modules[module_name] = load_module(module_name, prompts_dir=base_dir)
        except FileNotFoundError:
            continue

    return modules


def list_versions(name: str, prompts_dir: Path | None = None) -> list[int]:
    """
    List all available versions of a prompt module.

    Returns:
        Sorted list of version numbers.
    """
    base_dir = prompts_dir or _PROMPTS_DIR
    versions_dir = base_dir / "versions" / name.replace("/", os.sep)

    if not versions_dir.exists():
        return []

    versions: list[int] = []
    for f in versions_dir.glob("v*.md"):
        match = re.match(r"v(\d+)\.md", f.name)
        if match:
            versions.append(int(match.group(1)))

    return sorted(versions)
