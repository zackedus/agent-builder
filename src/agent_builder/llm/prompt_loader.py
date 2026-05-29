"""Load and render prompt templates from ``llm/prompts/*.txt``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from string import Formatter

from agent_builder.llm.exceptions import LLMError

PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptNotFoundError(LLMError):
    """Raised when a prompt template file does not exist."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Prompt template not found: {name}.txt")
        self.template_name = name


class PromptRenderError(LLMError):
    """Raised when template variables are missing or invalid."""


@lru_cache(maxsize=32)
def load_template(name: str) -> str:
    """Load a prompt template by name (without ``.txt`` extension)."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        raise PromptNotFoundError(name)
    return path.read_text(encoding="utf-8")


def list_templates() -> list[str]:
    """Return available template names."""
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.txt"))


def render_prompt(template: str, variables: dict[str, str] | None = None) -> str:
    """Render a template with ``str.format``-style placeholders."""
    variables = variables or {}
    required = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    missing = required - set(variables.keys())
    if missing:
        raise PromptRenderError(f"Missing prompt variables: {sorted(missing)}")
    try:
        return template.format(**variables)
    except (KeyError, ValueError) as exc:
        raise PromptRenderError(f"Failed to render prompt: {exc}") from exc


def load_and_render(name: str, variables: dict[str, str] | None = None) -> str:
    """Load template file and render with variables."""
    return render_prompt(load_template(name), variables)
