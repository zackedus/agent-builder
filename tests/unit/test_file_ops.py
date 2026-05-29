import pytest

from agent_builder.core.workspace import Workspace
from agent_builder.tools.file_ops import (
    PathTraversalError,
    read_project_file,
    resolve_project_path,
    write_project_file,
    write_project_files,
)


def test_write_and_read_project_file(workspace: Workspace) -> None:
    path = write_project_file(workspace, "src/main.py", 'print("ok")\n')
    assert path.is_file()
    assert read_project_file(workspace, "src/main.py") == 'print("ok")\n'


def test_write_multiple_files(workspace: Workspace) -> None:
    written = write_project_files(
        workspace,
        {"a.py": "a = 1\n", "pkg/b.py": "b = 2\n"},
    )
    assert len(written) == 2
    assert read_project_file(workspace, "pkg/b.py") == "b = 2\n"


def test_path_traversal_rejected(workspace: Workspace) -> None:
    with pytest.raises(PathTraversalError):
        resolve_project_path(workspace, "../outside.py")
