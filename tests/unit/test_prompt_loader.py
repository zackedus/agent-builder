import pytest

from agent_builder.llm.prompt_loader import (
    PromptNotFoundError,
    PromptRenderError,
    list_templates,
    load_and_render,
    load_template,
    render_prompt,
)


def test_list_templates_includes_planner() -> None:
    names = list_templates()
    assert "planner" in names
    assert "coder" in names


def test_load_template_planner() -> None:
    text = load_template("planner")
    assert "{user_prompt}" in text


def test_render_prompt_substitutes_variables() -> None:
    rendered = render_prompt("Hello {name}!", {"name": "World"})
    assert rendered == "Hello World!"


def test_render_prompt_missing_variable_raises() -> None:
    with pytest.raises(PromptRenderError):
        render_prompt("Hello {name}!", {})


def test_load_and_render_coder() -> None:
    text = load_and_render(
        "coder",
        {
            "task_id": "T1",
            "task_title": "Setup",
            "task_type": "scaffold",
            "user_prompt": "Todo app",
            "context": "No files yet.",
            "files_affected": "main.py",
        },
    )
    assert "T1" in text
    assert "Todo app" in text


def test_load_missing_template_raises() -> None:
    with pytest.raises(PromptNotFoundError):
        load_template("nonexistent_template_xyz")
