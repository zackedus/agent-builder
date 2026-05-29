from pathlib import Path

from agent_builder.core.logging_setup import configure_logging, get_agent_logger, is_configured
from agent_builder.core.workspace import Workspace


def test_configure_logging_creates_agent_log_files(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "ws")
    configure_logging(workspace, level="DEBUG", console=False)

    log = get_agent_logger("coder")
    log.info("test message for coder")

    coder_log = workspace.logs_dir / "coder.log"
    assert coder_log.is_file()
    content = coder_log.read_text(encoding="utf-8")
    assert "test message for coder" in content
    assert is_configured() is True
