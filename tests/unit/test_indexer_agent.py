"""Unit tests for Indexer agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.indexer import IndexerAgent
from agent_builder.config import Settings
from agent_builder.core.workspace import Workspace
from agent_builder.indexing.chroma_store import ChromaCodeStore
from agent_builder.llm.router import LLMRouter


@pytest.fixture
def index_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "idx_ws")
    ws.ensure_layout()
    (ws.project_dir / "app.py").write_text(
        "def run() -> int:\n    return 42\n",
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))


@pytest.mark.asyncio
async def test_indexer_indexes_with_mocked_embed(
    index_workspace: Workspace,
    router: LLMRouter,
) -> None:
    agent = IndexerAgent(router, index_workspace)

    mock_embedder = MagicMock()
    mock_embedder.healthy.return_value = True
    mock_embedder.embed_texts = AsyncMock(return_value=[[0.5, 0.5, 0.5]])

    with patch("agent_builder.agents.indexer.OllamaEmbedder", return_value=mock_embedder):
        count = await agent.index_project(paths=["app.py"])

    assert count >= 1
    store = ChromaCodeStore(index_workspace.vectordb_dir)
    assert store.count >= 1


@pytest.mark.asyncio
async def test_indexer_execute_via_run(
    index_workspace: Workspace,
    router: LLMRouter,
) -> None:
    agent = IndexerAgent(router, index_workspace)

    with patch.object(agent, "index_project", AsyncMock(return_value=2)):
        result = await agent.run(
            AgentContext(
                session_id="s1",
                extra={"files_to_index": ["app.py"]},
            ),
        )

    assert result.success is True
    assert result.data["chunks_indexed"] == 2
