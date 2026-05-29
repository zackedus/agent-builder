"""Unit tests for AST-aware code chunker."""

from __future__ import annotations

from pathlib import Path

from agent_builder.indexing.chunker import chunk_python_file, chunk_python_source

SAMPLE = '''
"""Sample module."""
import os

class Greeter:
    def greet(self, name: str) -> str:
        return f"hi {name}"

def shout(msg: str) -> str:
    return msg.upper()
'''


def test_chunk_python_source_splits_symbols() -> None:
    chunks = chunk_python_source("demo.py", SAMPLE)
    symbols = {c.symbol for c in chunks}
    assert "Greeter" in symbols
    assert "Greeter.greet" in symbols
    assert "shout" in symbols


def test_chunk_python_file(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    path = project / "demo.py"
    path.write_text(SAMPLE, encoding="utf-8")
    chunks = chunk_python_file(path, project)
    assert any(c.symbol_type == "function" for c in chunks)
