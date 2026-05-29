"""Ollama embedding client for code chunks."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from agent_builder.config import Settings
from agent_builder.llm.exceptions import LLMProviderError

try:
    from ollama import AsyncClient
except ImportError:  # pragma: no cover
    AsyncClient = None

EMBED_BATCH_SIZE = 32


class OllamaEmbedder:
    """Embed text via Ollama ``/api/embed`` (``nomic-embed-text`` by default)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.ollama_model_embed
        self._host = settings.ollama_host.rstrip("/")
        self._client: Any = None
        if AsyncClient is not None:
            self._client = AsyncClient(host=self._host)

    def healthy(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return bool(resp.status == 200)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input string."""
        if not texts:
            return []
        if self._client is None:
            raise LLMProviderError("Ollama client is not available")

        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            try:
                response = await self._client.embed(model=self._model, input=batch)
            except Exception as exc:
                raise LLMProviderError(f"Ollama embed failed: {exc}") from exc

            batch_vectors = _extract_embeddings(response)
            if len(batch_vectors) != len(batch):
                raise LLMProviderError(
                    f"Expected {len(batch)} embeddings, got {len(batch_vectors)}"
                )
            vectors.extend(batch_vectors)
        return vectors


def _extract_embeddings(response: Any) -> list[list[float]]:
    if isinstance(response, dict):
        raw = response.get("embeddings", [])
    else:
        raw = getattr(response, "embeddings", [])
    return [[float(x) for x in vec] for vec in raw]
