"""Search API for agents — query the workspace code index."""

from __future__ import annotations

from agent_builder.config import Settings, get_settings
from agent_builder.core.workspace import Workspace
from agent_builder.indexing.chroma_store import ChromaCodeStore, SearchHit
from agent_builder.indexing.embedder import OllamaEmbedder


async def search_relevant_chunks(
    workspace: Workspace,
    query: str,
    *,
    top_k: int = 5,
    settings: Settings | None = None,
) -> list[SearchHit]:
    """Semantic search over indexed project code."""
    cfg = settings or get_settings()
    store = ChromaCodeStore(workspace.vectordb_dir)
    if store.count == 0:
        return []

    embedder = OllamaEmbedder(cfg)
    if not embedder.healthy():
        return []

    vectors = await embedder.embed_texts([query])
    if not vectors:
        return []
    return store.search(vectors[0], top_k=top_k)


async def search_relevant_files(
    workspace: Workspace,
    query: str,
    *,
    top_k: int = 5,
    settings: Settings | None = None,
) -> list[str]:
    """Return unique file paths most relevant to *query*."""
    hits = await search_relevant_chunks(
        workspace,
        query,
        top_k=top_k,
        settings=settings,
    )
    seen: set[str] = set()
    paths: list[str] = []
    for hit in hits:
        if hit.file_path and hit.file_path not in seen:
            seen.add(hit.file_path)
            paths.append(hit.file_path)
    return paths
