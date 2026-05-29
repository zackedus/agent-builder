"""Watch ``workspace/project/`` and queue Python files for re-indexing."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_builder.agents.indexer import IndexerAgent

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover
    FileSystemEventHandler = object
    Observer = None


def _is_indexable_py(rel_path: str) -> bool:
    if not rel_path.endswith(".py"):
        return False
    return "__pycache__" not in rel_path.split("/")


class _ProjectIndexHandler(FileSystemEventHandler):
    def __init__(self, watcher: ProjectIndexWatcher) -> None:
        self._watcher = watcher

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher.mark_path(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher.mark_path(str(event.src_path))


class ProjectIndexWatcher:
    """Collect ``.py`` changes under a project directory for debounced re-index."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir.resolve()
        self._lock = threading.Lock()
        self._pending: set[str] = set()
        self._observer: Any = None
        self._handler: _ProjectIndexHandler | None = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None

    def mark_path(self, path: str | Path) -> None:
        """Queue a file (absolute or relative) for the next ``flush``."""
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = (self._project_dir / resolved).resolve()
        else:
            resolved = resolved.resolve()

        if resolved.suffix != ".py":
            return
        try:
            rel = resolved.relative_to(self._project_dir).as_posix()
        except ValueError:
            return
        if not _is_indexable_py(rel):
            return
        with self._lock:
            self._pending.add(rel)

    def drain_pending(self) -> list[str]:
        """Return and clear queued relative paths."""
        with self._lock:
            paths = sorted(self._pending)
            self._pending.clear()
        return paths

    def start(self) -> bool:
        """Start filesystem observer; return False if watchdog is unavailable."""
        if Observer is None or self._observer is not None:
            return self._observer is not None

        self._project_dir.mkdir(parents=True, exist_ok=True)
        self._handler = _ProjectIndexHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._project_dir), recursive=True)
        self._observer.start()
        return True

    def stop(self) -> None:
        """Stop the observer thread."""
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5.0)
        self._observer = None
        self._handler = None

    async def flush(self, indexer: IndexerAgent) -> int:
        """Re-index all pending files via *indexer*."""
        paths = self.drain_pending()
        if not paths:
            return 0
        return await indexer.index_project(paths=paths)
