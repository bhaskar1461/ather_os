"""
Prompt Optimizer

Removes duplicate instructions, compresses whitespace, merges similar lines,
and reduces token usage while preserving semantic meaning.
"""

import re


def optimize_prompt_content(content: str) -> str:
    """
    Optimize a raw prompt string by removing redundancies and compressing whitespace.

    Operations:
    1. Remove duplicate lines
    2. Collapse excessive blank lines
    3. Strip trailing whitespace
    4. Remove redundant bullet markers
    """
    if not content.strip():
        return ""

    lines = content.split("\n")
    seen_lines: set[str] = set()
    optimized: list[str] = []
    blank_count = 0

    for line in lines:
        stripped = line.strip()

        # Collapse multiple blank lines into one
        if not stripped:
            blank_count += 1
            if blank_count <= 2:
                optimized.append("")
            continue
        else:
            blank_count = 0

        # Normalize the line for deduplication (lowercase, collapse spaces)
        normalized = re.sub(r"\s+", " ", stripped.lower())

        if normalized in seen_lines:
            continue

        seen_lines.add(normalized)
        optimized.append(line.rstrip())

    result = "\n".join(optimized).strip()

    # Collapse 3+ consecutive newlines into 2
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


def truncate_to_token_budget(content: str, max_tokens: int) -> str:
    """
    Truncate content to fit within a token budget.
    Uses a conservative 4-chars-per-token estimate.
    Truncates at sentence boundaries when possible.
    """
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content

    truncated = content[:max_chars]

    # Try to truncate at the last sentence boundary
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    cut_point = max(last_period, last_newline)

    if cut_point > max_chars * 0.7:
        truncated = truncated[:cut_point + 1]

    return truncated.strip()


def merge_similar_instructions(instructions: list[str], similarity_threshold: float = 0.85) -> list[str]:
    """
    Merge instructions that are highly similar (based on word overlap).
    Keeps the longer version when two instructions are near-duplicates.
    """
    if len(instructions) <= 1:
        return instructions

    def word_set(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower()))

    def jaccard_similarity(a: set[str], b: set[str]) -> float:
        if not a and not b:
            return 1.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0

    merged: list[str] = []
    used: set[int] = set()

    for i, inst_a in enumerate(instructions):
        if i in used:
            continue
        best = inst_a
        words_a = word_set(inst_a)

        for j, inst_b in enumerate(instructions[i + 1:], start=i + 1):
            if j in used:
                continue
            words_b = word_set(inst_b)
            if jaccard_similarity(words_a, words_b) >= similarity_threshold:
                # Keep the longer one
                if len(inst_b) > len(best):
                    best = inst_b
                used.add(j)

        merged.append(best)
        used.add(i)

    return merged
