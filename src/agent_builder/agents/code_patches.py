"""Apply SEARCH/REPLACE patch blocks from Coder output."""

from __future__ import annotations

import re

from agent_builder.llm.exceptions import LLMError

_SEARCH_REPLACE_RE = re.compile(
    r"<<<<<<< SEARCH\r?\n(?P<search>[\s\S]*?)\r?\n=======\r?\n"
    r"(?P<replace>[\s\S]*?)\r?\n>>>>>>> REPLACE",
    re.MULTILINE,
)


class PatchApplyError(LLMError):
    """Failed to apply a SEARCH/REPLACE block."""


def parse_search_replace_blocks(body: str) -> list[tuple[str, str]]:
    """Parse Aider-style SEARCH/REPLACE blocks from a code fence body."""
    blocks: list[tuple[str, str]] = []
    for match in _SEARCH_REPLACE_RE.finditer(body):
        blocks.append((match.group("search"), match.group("replace")))
    return blocks


def has_search_replace_blocks(body: str) -> bool:
    return "<<<<<<< SEARCH" in body


def apply_search_replace(original: str, search: str, replace: str) -> str:
    """Replace exactly one occurrence of *search* with *replace*."""
    count = original.count(search)
    if count == 0:
        raise PatchApplyError("SEARCH block did not match any content in the file")
    if count > 1:
        raise PatchApplyError(f"SEARCH block matched {count} times; must be unique")
    return original.replace(search, replace, 1)


def apply_all_patches(original: str, blocks: list[tuple[str, str]]) -> str:
    """Apply patch blocks in order to *original* source."""
    updated = original
    for search, replace in blocks:
        updated = apply_search_replace(updated, search, replace)
    return updated
