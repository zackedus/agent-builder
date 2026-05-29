"""Build Coder prompt context from the code index and existing project files."""

from __future__ import annotations

from agent_builder.config import Settings
from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.indexing.chroma_store import SearchHit
from agent_builder.indexing.search import search_relevant_chunks
from agent_builder.llm.prompt_loader import load_template
from agent_builder.tools.file_ops import read_project_file


def build_coder_search_query(
    *,
    user_prompt: str,
    plan_task: PlanTask | None,
) -> str:
    """Compose a semantic search query for the code index."""
    parts: list[str] = []
    if plan_task:
        parts.append(plan_task.title)
        if plan_task.acceptance_criteria:
            parts.extend(plan_task.acceptance_criteria[:3])
        parts.extend(plan_task.files_affected[:5])
    if user_prompt:
        parts.append(user_prompt[:500])
    return " ".join(parts).strip() or "project code"


async def fetch_index_hits(
    workspace: Workspace,
    query: str,
    *,
    settings: Settings | None = None,
    top_k: int = 5,
) -> list[SearchHit]:
    """Return semantic search hits, or empty when the index is unavailable."""
    return await search_relevant_chunks(
        workspace,
        query,
        top_k=top_k,
        settings=settings,
    )


def format_index_context(hits: list[SearchHit]) -> str:
    """Format search hits for inclusion in the Coder prompt."""
    if not hits:
        return ""
    lines = ["Relevant code from project index (semantic search):"]
    for hit in hits:
        lines.append(
            f"\n--- {hit.file_path} :: {hit.symbol_type} {hit.symbol} "
            f"(score {hit.score:.3f}) ---\n{hit.content.rstrip()}"
        )
    return "\n".join(lines)


def collect_context_paths(
    plan_task: PlanTask | None,
    hits: list[SearchHit],
) -> list[str]:
    """Paths to load as existing-file context (task files + index hits)."""
    paths: list[str] = []
    if plan_task:
        for rel in plan_task.files_affected:
            norm = rel.replace("\\", "/").lstrip("/")
            if norm and norm not in paths:
                paths.append(norm)
    for hit in hits:
        if hit.file_path and hit.file_path not in paths:
            paths.append(hit.file_path)
    return paths


def format_existing_files_context(workspace: Workspace, paths: list[str]) -> str:
    """Load current project file contents for edit/patch tasks."""
    if not paths:
        return ""
    sections: list[str] = ["Existing project files (use SEARCH/REPLACE patches when editing):"]
    for rel in paths:
        try:
            content = read_project_file(workspace, rel)
            sections.append(f"\n--- file: {rel} ---\n{content.rstrip()}\n")
        except WorkspaceError:
            sections.append(f"\n--- file: {rel} (new file, no existing content) ---")
    return "\n".join(sections)


def format_flet_context(plan_task: PlanTask | None, *, has_design: bool) -> str:
    """Attach Flet widget reference when building UI tasks."""
    if plan_task is None:
        return ""
    if plan_task.type != "ui" and not has_design:
        return ""
    try:
        return load_template("flet_reference")
    except OSError:
        return ""
