"""Code indexer agent — chunk, embed, and store in ChromaDB."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.config import Settings, get_settings
from agent_builder.core.workspace import Workspace
from agent_builder.indexing.chroma_store import ChromaCodeStore, SearchHit
from agent_builder.indexing.chunker import chunk_project
from agent_builder.indexing.embedder import OllamaEmbedder
from agent_builder.indexing.search import search_relevant_chunks
from agent_builder.llm.router import LLMRouter


class IndexerAgent(BaseAgent):
    """Builds and queries a semantic index of ``workspace/project/``."""

    name = "indexer"
    max_retries = 1

    def __init__(
        self,
        router: LLMRouter,
        workspace: Workspace | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(router, workspace)
        self.settings = settings or get_settings()

    async def execute(self, context: AgentContext) -> AgentResult:
        if self.workspace is None:
            return AgentResult(success=False, output="Workspace is required for Indexer")

        paths: list[str] | None = context.extra.get("files_to_index")
        indexed = await self.index_project(paths=paths)
        return AgentResult(
            success=True,
            output=f"indexed {indexed} chunk(s)",
            data={"chunks_indexed": indexed},
        )

    def validate_result(self, result: AgentResult) -> bool:
        return result.success

    async def index_project(self, *, paths: list[str] | None = None) -> int:
        """Chunk project files, embed, and upsert into ChromaDB."""
        assert self.workspace is not None
        project_dir = self.workspace.project_dir
        if not project_dir.is_dir():
            return 0

        chunks = chunk_project(project_dir, paths=paths)
        if not chunks:
            return 0

        embedder = OllamaEmbedder(self.settings)
        if not embedder.healthy():
            return 0

        texts = [chunk.content for chunk in chunks]
        embeddings = await embedder.embed_texts(texts)

        store = ChromaCodeStore(self.workspace.vectordb_dir)
        if paths:
            for rel in paths:
                store.delete_by_file(rel.replace("\\", "/"))
        return store.upsert_chunks(chunks, embeddings)

    async def search(self, query: str, *, top_k: int = 5) -> list[SearchHit]:
        """Search the workspace index (delegates to ``search_relevant_chunks``)."""
        assert self.workspace is not None
        return await search_relevant_chunks(
            self.workspace,
            query,
            top_k=top_k,
            settings=self.settings,
        )
