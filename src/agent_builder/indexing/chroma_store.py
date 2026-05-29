"""ChromaDB persistence for code chunk embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agent_builder.indexing.chunker import CodeChunk

COLLECTION_NAME = "code_chunks"


@dataclass(frozen=True)
class SearchHit:
    """One semantic search result."""

    chunk_id: str
    file_path: str
    symbol: str
    symbol_type: str
    content: str
    score: float


class ChromaCodeStore:
    """Persist and query code chunks in ChromaDB."""

    def __init__(self, persist_dir: Path) -> None:
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return int(self._collection.count())

    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> int:
        """Insert or update chunks with precomputed embeddings."""
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas: list[dict[str, str | int]] = [
            {
                "file_path": chunk.file_path,
                "symbol": chunk.symbol,
                "symbol_type": chunk.symbol_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "imports": ",".join(chunk.imports),
            }
            for chunk in chunks
        ]
        self._collection.upsert(
            ids=ids,
            embeddings=cast(Any, embeddings),
            documents=documents,
            metadatas=cast(Any, metadatas),
        )
        return len(ids)

    def delete_by_file(self, file_path: str) -> None:
        """Remove all chunks for *file_path* (posix-style relative path)."""
        try:
            self._collection.delete(where={"file_path": file_path})
        except Exception:
            pass

    def search(self, query_embedding: list[float], *, top_k: int = 5) -> list[SearchHit]:
        """Return the closest chunks to *query_embedding*."""
        if self.count == 0:
            return []

        result = cast(
            dict[str, Any],
            self._collection.query(
                query_embeddings=cast(Any, [query_embedding]),
                n_results=min(top_k, self.count),
                include=["documents", "metadatas", "distances"],
            ),
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[SearchHit] = []
        for idx, chunk_id in enumerate(ids):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            doc = documents[idx] if idx < len(documents) else ""
            dist = float(distances[idx]) if idx < len(distances) else 1.0
            score = max(0.0, 1.0 - dist)
            hits.append(
                SearchHit(
                    chunk_id=str(chunk_id),
                    file_path=str(meta.get("file_path", "")),
                    symbol=str(meta.get("symbol", "")),
                    symbol_type=str(meta.get("symbol_type", "")),
                    content=str(doc or ""),
                    score=round(score, 4),
                )
            )
        return hits
