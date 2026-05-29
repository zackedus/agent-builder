import pytest

from agent_builder.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("ANTHROPIC_API_KEY", "OLLAMA_HOST", "AGENT_BUILDER_WORKSPACE"):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None, _env_ignore=True)
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.log_level == "INFO"
    assert settings.anthropic_configured() is False


def test_anthropic_configured_when_key_set() -> None:
    settings = Settings(
        anthropic_api_key="sk-test",
        _env_file=None,
        _env_ignore=True,
    )
    assert settings.anthropic_configured() is True
