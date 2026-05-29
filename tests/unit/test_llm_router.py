from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.config import Settings
from agent_builder.core.event_bus import EventBus, EventType
from agent_builder.llm.cost_tracker import CostTracker, estimate_cost
from agent_builder.llm.exceptions import LLMProviderError
from agent_builder.llm.router import OLLAMA_ALIAS, OPUS_ALIAS, SONNET_ALIAS, LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        _env_file=None,
        _env_ignore=True,
    )


@pytest.fixture
def router(settings: Settings) -> LLMRouter:
    return LLMRouter(settings)


def test_decide_planner_uses_opus(router: LLMRouter) -> None:
    decision = router.decide(RouteRequest(agent="planner"))
    assert decision.primary == OPUS_ALIAS
    assert decision.fallback == SONNET_ALIAS


def test_decide_coder_scaffold_prefers_ollama(router: LLMRouter) -> None:
    decision = router.decide(RouteRequest(agent="coder", task_type="scaffold"))
    assert decision.primary == OLLAMA_ALIAS
    assert decision.fallback == SONNET_ALIAS


def test_decide_coder_refactor_uses_opus(router: LLMRouter) -> None:
    decision = router.decide(RouteRequest(agent="coder", task_type="refactor"))
    assert decision.primary == OPUS_ALIAS


def test_decide_reviewer_uses_opus(router: LLMRouter) -> None:
    decision = router.decide(RouteRequest(agent="reviewer"))
    assert decision.primary == OPUS_ALIAS


def test_route_falls_back_when_ollama_unhealthy(settings: Settings) -> None:
    router = LLMRouter(settings)
    with patch.object(router._ollama_coder, "healthy", return_value=False):
        with patch.object(router._claude_sonnet, "healthy", return_value=True):
            client = router.route(RouteRequest(agent="coder", task_type="scaffold"))
    assert client.model_alias == SONNET_ALIAS


@pytest.mark.asyncio
async def test_complete_failover_to_fallback(settings: Settings) -> None:
    router = LLMRouter(settings)
    expected = LLMResponse(
        text="ok",
        model=SONNET_ALIAS,
        provider="anthropic",
        usage=LLMUsage(input_tokens=10, output_tokens=5),
    )

    with patch.object(router._ollama_coder, "healthy", return_value=True):
        with patch.object(
            router._ollama_coder,
            "complete",
            AsyncMock(side_effect=LLMProviderError("ollama fail")),
        ):
            with patch.object(
                router._claude_sonnet,
                "complete",
                AsyncMock(return_value=expected),
            ):
                with patch.object(router._claude_sonnet, "healthy", return_value=True):
                    response = await router.complete(
                        RouteRequest(agent="coder", task_type="scaffold"),
                        [LLMMessage(role="user", content="hi")],
                    )
    assert response.text == "ok"


@pytest.mark.asyncio
async def test_complete_emits_llm_call_event(settings: Settings) -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []
    bus.subscribe(EventType.LLM_CALL, lambda e: received.append(e.payload))

    router = LLMRouter(settings, event_bus=bus, session_id="sess-1")
    expected = LLMResponse(
        text="hello",
        model=OPUS_ALIAS,
        provider="anthropic",
        usage=LLMUsage(input_tokens=100, output_tokens=50),
    )

    with patch.object(router._claude_opus, "healthy", return_value=True):
        with patch.object(
            router._claude_opus,
            "complete",
            AsyncMock(return_value=expected),
        ):
            await router.complete(
                RouteRequest(agent="planner"),
                [LLMMessage(role="user", content="plan")],
            )

    assert len(received) == 1
    assert received[0]["agent"] == "planner"
    assert received[0]["input_tokens"] == 100


def test_cost_tracker_from_llm_call_event() -> None:
    bus = EventBus()
    tracker = CostTracker(bus, budget_cap=1.0)
    from agent_builder.core.event_bus import Event

    tracker.on_llm_call(
        Event(
            type=EventType.LLM_CALL,
            session_id="s",
            payload={
                "agent": "planner",
                "model": OPUS_ALIAS,
                "input_tokens": 1_000_000,
                "output_tokens": 0,
            },
        )
    )
    assert tracker.total_cost_usd == pytest.approx(15.0)
    assert tracker.budget_exceeded is True


def test_estimate_cost_ollama_free() -> None:
    assert estimate_cost(OLLAMA_ALIAS, 5000, 5000) == 0.0
