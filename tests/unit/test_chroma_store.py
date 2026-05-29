"""Unit tests for ChromaDB code store."""

from __future__ import annotations

from pathlib import Path

from agent_builder.indexing.chroma_store import ChromaCodeStore
from agent_builder.indexing.chunker import CodeChunk


def _sample_chunk() -> CodeChunk:
    return CodeChunk(
        id="hello.py::greet",
        file_path="hello.py",
        symbol="greet",
        symbol_type="function",
        content="def greet() -> str:\n    return 'hi'\n",
        start_line=1,
        end_line=2,
    )


def test_chroma_upsert_and_search(tmp_path: Path) -> None:
    store = ChromaCodeStore(tmp_path / "vectordb")
    chunk = _sample_chunk()
    embedding = [0.1, 0.2, 0.3, 0.4]
    assert store.upsert_chunks([chunk], [embedding]) == 1
    assert store.count == 1

    hits = store.search(embedding, top_k=1)
    assert len(hits) == 1
    assert hits[0].file_path == "hello.py"
    assert hits[0].symbol == "greet"


def test_chroma_delete_by_file(tmp_path: Path) -> None:
    store = ChromaCodeStore(tmp_path / "vectordb2")
    chunk = _sample_chunk()
    embedding = [1.0, 0.0, 0.0]
    store.upsert_chunks([chunk], [embedding])
    store.delete_by_file("hello.py")
    assert store.count == 0
