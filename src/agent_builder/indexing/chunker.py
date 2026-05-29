"""AST-aware Python code chunking for semantic index."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from agent_builder.validation.project_output import find_python_files

SymbolType = Literal["function", "class", "method", "module"]


@dataclass(frozen=True)
class CodeChunk:
    """One indexable unit of Python source (function, class, or module)."""

    id: str
    file_path: str
    symbol: str
    symbol_type: SymbolType
    content: str
    start_line: int
    end_line: int
    imports: tuple[str, ...] = field(default_factory=tuple)


def _extract_imports(tree: ast.Module) -> tuple[str, ...]:
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


def _source_for_node(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment
    lines = source.splitlines()
    start = max(getattr(node, "lineno", 1) - 1, 0)
    end = getattr(node, "end_lineno", start + 1) or start + 1
    return "\n".join(lines[start:end])


def _make_chunk(
    *,
    rel_path: str,
    symbol: str,
    symbol_type: SymbolType,
    source: str,
    node: ast.AST,
    imports: tuple[str, ...],
) -> CodeChunk:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start) or start
    chunk_id = f"{rel_path}::{symbol}"
    return CodeChunk(
        id=chunk_id,
        file_path=rel_path,
        symbol=symbol,
        symbol_type=symbol_type,
        content=_source_for_node(source, node),
        start_line=start,
        end_line=end,
        imports=imports,
    )


def chunk_python_source(rel_path: str, source: str) -> list[CodeChunk]:
    """Split *source* into function/class/method chunks."""
    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return [
            CodeChunk(
                id=f"{rel_path}::module",
                file_path=rel_path,
                symbol="module",
                symbol_type="module",
                content=source[:8000],
                start_line=1,
                end_line=max(source.count("\n") + 1, 1),
            )
        ]

    if not isinstance(tree, ast.Module):
        return []

    imports = _extract_imports(tree)
    chunks: list[CodeChunk] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            chunks.append(
                _make_chunk(
                    rel_path=rel_path,
                    symbol=node.name,
                    symbol_type="function",
                    source=source,
                    node=node,
                    imports=imports,
                )
            )
        elif isinstance(node, ast.ClassDef):
            chunks.append(
                _make_chunk(
                    rel_path=rel_path,
                    symbol=node.name,
                    symbol_type="class",
                    source=source,
                    node=node,
                    imports=imports,
                )
            )
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    method_name = f"{node.name}.{item.name}"
                    chunks.append(
                        _make_chunk(
                            rel_path=rel_path,
                            symbol=method_name,
                            symbol_type="method",
                            source=source,
                            node=item,
                            imports=imports,
                        )
                    )

    if not chunks:
        chunks.append(
            CodeChunk(
                id=f"{rel_path}::module",
                file_path=rel_path,
                symbol="module",
                symbol_type="module",
                content=source[:8000],
                start_line=1,
                end_line=max(source.count("\n") + 1, 1),
                imports=imports,
            )
        )
    return chunks


def chunk_python_file(path: Path, project_root: Path) -> list[CodeChunk]:
    """Chunk a single ``.py`` file relative to *project_root*."""
    rel = path.relative_to(project_root).as_posix()
    source = path.read_text(encoding="utf-8")
    return chunk_python_source(rel, source)


def chunk_project(project_dir: Path, *, paths: list[str] | None = None) -> list[CodeChunk]:
    """Chunk all (or selected) Python files under *project_dir*."""
    if paths:
        files = []
        for rel in paths:
            candidate = (project_dir / rel.replace("\\", "/")).resolve()
            if candidate.is_file() and candidate.suffix == ".py":
                files.append(candidate)
    else:
        files = find_python_files(project_dir)

    chunks: list[CodeChunk] = []
    for path in files:
        chunks.extend(chunk_python_file(path, project_dir))
    return chunks
