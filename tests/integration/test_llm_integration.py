"""Integration tests for real LLM providers (opt-in via env)."""

import pytest

from agent_builder.config import Settings, get_settings
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, RouteRequest

pytestmark = pytest.mark.integration


@pytest.fixture
def live_settings() -> Settings:
    settings = get_settings()
    if not settings.run_integration_tests:
        pytest.skip("Set AGENT_BUILDER_RUN_INTEGRATION_TESTS=true to run")
    if not settings.anthropic_configured():
        pytest.skip("ANTHROPIC_API_KEY required for LLM integration tests")
    return settings


@pytest.mark.asyncio
async def test_claude_live_completion(live_settings: Settings) -> None:
    router = LLMRouter(live_settings)
    response = await router.complete(
        RouteRequest(agent="tester", task_type="default"),
        [LLMMessage(role="user", content="Reply with exactly: pong")],
        max_tokens=32,
    )
    assert "pong" in response.text.lower()
    assert response.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_ollama_live_when_available(live_settings: Settings) -> None:
    router = LLMRouter(live_settings)
    if not router._ollama_coder.healthy():
        pytest.skip("Ollama is not running")

    response = await router.complete(
        RouteRequest(agent="coder", task_type="scaffold"),
        [LLMMessage(role="user", content="Reply with exactly: pong")],
        max_tokens=32,
    )
    assert len(response.text.strip()) > 0
