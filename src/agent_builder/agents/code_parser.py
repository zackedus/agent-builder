"""Extract file paths and source from LLM markdown responses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_builder.llm.exceptions import LLMError

_FENCE_RE = re.compile(r"```([^\n`]*)\r?\n([\s\S]*?)```", re.MULTILINE)
_FILE_HEADER_RE = re.compile(
    r"^\s*(?:#|//)\s*file:\s*(?P<path>[^\s#]+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


class CodeParseError(LLMError):
    """Failed to extract code files from model output."""


@dataclass(frozen=True)
class CodeFile:
    path: str
    content: str
    language: str | None = None


def _parse_fence_info(info: str) -> tuple[str | None, str | None]:
    """Return (language, path) from fence info string e.g. ``python:main.py``."""
    token = info.strip()
    if not token:
        return None, None
    if ":" in token:
        lang_part, path_part = token.split(":", 1)
        return lang_part.strip() or None, path_part.strip() or None
    if "." in token and "/" not in token and " " not in token:
        return None, token
    return token, None


def extract_code_files(
    text: str,
    *,
    default_paths: list[str] | None = None,
) -> list[CodeFile]:
    """Parse markdown fences (and optional ``# file:`` headers) into files."""
    stripped = text.strip()
    if not stripped:
        raise CodeParseError("Empty coder response")

    files: dict[str, CodeFile] = {}
    defaults = list(default_paths or [])
    default_iter = iter(defaults)

    for match in _FENCE_RE.finditer(stripped):
        info, body = match.group(1), match.group(2)
        language, path = _parse_fence_info(info)

        header_match = _FILE_HEADER_RE.search(body)
        if header_match:
            path = header_match.group("path").strip()
            body = body[header_match.end() :].lstrip("\n")

        if not path:
            path = next(default_iter, None)

        if not path:
            continue

        normalized = path.replace("\\", "/").lstrip("/")
        content = body.rstrip("\n") + "\n"
        files[normalized] = CodeFile(path=normalized, content=content, language=language)

    if files:
        return list(files.values())

    if len(defaults) == 1:
        return [CodeFile(path=defaults[0].replace("\\", "/").lstrip("/"), content=stripped + "\n")]

    raise CodeParseError("No code blocks with file paths found in coder response")
