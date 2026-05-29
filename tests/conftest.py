from pathlib import Path

import pytest

from agent_builder.core.workspace import Workspace


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "workspace")
    ws.ensure_layout()
    return ws
