"""Unit tests for SEARCH/REPLACE patch parsing and application."""

from __future__ import annotations

import pytest

from agent_builder.agents.code_parser import extract_code_files
from agent_builder.agents.code_patches import (
    PatchApplyError,
    apply_all_patches,
    apply_search_replace,
    parse_search_replace_blocks,
)


def test_parse_search_replace_blocks() -> None:
    body = """<<<<<<< SEARCH
old line
=======
new line
>>>>>>> REPLACE
"""
    blocks = parse_search_replace_blocks(body)
    assert blocks == [("old line", "new line")]


def test_apply_search_replace_unique_match() -> None:
    original = "alpha\nbeta\ngamma\n"
    updated = apply_search_replace(original, "beta\n", "BETA\n")
    assert updated == "alpha\nBETA\ngamma\n"


def test_apply_search_replace_rejects_ambiguous() -> None:
    with pytest.raises(PatchApplyError, match="2 times"):
        apply_search_replace("x\nx\n", "x\n", "y\n")


def test_extract_code_files_parses_patches() -> None:
    text = """```python:app.py
<<<<<<< SEARCH
def old():
    pass
=======
def new():
    return 1
>>>>>>> REPLACE
```"""
    files = extract_code_files(text, default_paths=["app.py"])
    assert len(files) == 1
    assert files[0].patches
    assert files[0].content == ""


def test_apply_all_patches_sequence() -> None:
    original = "a=1\nb=2\nc=3\n"
    result = apply_all_patches(
        original,
        [("a=1\n", "a=10\n"), ("c=3\n", "c=30\n")],
    )
    assert result == "a=10\nb=2\nc=30\n"
