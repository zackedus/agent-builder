"""Loguru configuration with per-agent log files."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger

from agent_builder.core.workspace import Workspace

RUNTIME_AGENT_NAMES: tuple[str, ...] = (
    "orchestrator",
    "planner",
    "indexer",
    "designer",
    "coder",
    "tester",
    "reviewer",
    "devops",
)

_configured = False


def configure_logging(
    workspace: Workspace,
    *,
    level: str = "INFO",
    console: bool = True,
) -> None:
    """Configure loguru: stderr + one rotating file per runtime agent."""
    global _configured
    logger.remove()
    if console:
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[agent]}</cyan> - "
                "<level>{message}</level>"
            ),
            filter=lambda record: "agent" in record["extra"],
        )
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<level>{message}</level>"
            ),
            filter=lambda record: "agent" not in record["extra"],
        )

    workspace.ensure_layout()
    log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[agent]} | {message}"
    for agent in RUNTIME_AGENT_NAMES:
        log_path = workspace.logs_dir / f"{agent}.log"
        logger.add(
            log_path,
            level=level,
            format=log_format,
            filter=_agent_filter(agent),
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )

    _configured = True


def _agent_filter(agent: str) -> Any:
    def _filter(record: Any) -> bool:
        return bool(record["extra"].get("agent") == agent)

    return _filter


def get_agent_logger(agent: str) -> Any:
    """Return a logger bound to a runtime agent name."""
    return logger.bind(agent=agent)


def is_configured() -> bool:
    return _configured
