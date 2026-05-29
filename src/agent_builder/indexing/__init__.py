"""AST-aware chunking, embeddings, and ChromaDB code index."""

from agent_builder.indexing.chroma_store import ChromaCodeStore, SearchHit
from agent_builder.indexing.chunker import CodeChunk, chunk_project, chunk_python_file
from agent_builder.indexing.embedder import OllamaEmbedder
from agent_builder.indexing.search import search_relevant_chunks, search_relevant_files
from agent_builder.indexing.watcher import ProjectIndexWatcher

__all__ = [
    "ProjectIndexWatcher",
    "ChromaCodeStore",
    "CodeChunk",
    "OllamaEmbedder",
    "SearchHit",
    "chunk_project",
    "chunk_python_file",
    "search_relevant_chunks",
    "search_relevant_files",
]
