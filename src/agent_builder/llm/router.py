"""Rule-based LLM router with health checks and failover."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.config import Settings
from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.llm.claude_client import ClaudeClient
from agent_builder.llm.cost_tracker import CostTracker
from agent_builder.llm.exceptions import LLMError, LLMProviderError
from agent_builder.llm.ollama_client import OllamaClient
from agent_builder.llm.types import LLMMessage, LLMResponse, RouteRequest

# Model aliases used in routing table and pricing
OPUS_ALIAS = "claude-opus-4-7"
SONNET_ALIAS = "claude-sonnet-4-6"
OLLAMA_ALIAS = "ollama"


@dataclass(frozen=True)
class RouteDecision:
    primary: str
    fallback: str | None


class LLMRouter:
    """Selects LLM provider per agent/task and completes with failover."""

    def __init__(
        self,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
        session_id: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus
        self._session_id = session_id

        self._claude_opus = ClaudeClient(
            settings,
            model=settings.claude_model_opus,
            model_alias=OPUS_ALIAS,
        )
        self._claude_sonnet = ClaudeClient(
            settings,
            model=settings.claude_model_sonnet,
            model_alias=SONNET_ALIAS,
        )
        self._ollama_coder = OllamaClient(
            settings,
            model=settings.ollama_model_coder,
            model_alias=OLLAMA_ALIAS,
        )
        self._ollama_embed = OllamaClient(
            settings,
            model=settings.ollama_model_embed,
            model_alias=OLLAMA_ALIAS,
        )

        self._clients: dict[str, ClaudeClient | OllamaClient] = {
            OPUS_ALIAS: self._claude_opus,
            SONNET_ALIAS: self._claude_sonnet,
            OLLAMA_ALIAS: self._ollama_coder,
        }

        self.cost_tracker = cost_tracker
        if cost_tracker is None and event_bus is not None:
            self.cost_tracker = CostTracker(event_bus, budget_cap=settings.budget_usd)

    def decide(self, request: RouteRequest) -> RouteDecision:
        """Return primary and fallback model aliases for a route request."""
        agent = request.agent.lower()
        task_type = request.task_type.lower()

        if agent == "planner":
            return RouteDecision(OPUS_ALIAS, SONNET_ALIAS)
        if agent == "reviewer":
            return RouteDecision(OPUS_ALIAS, SONNET_ALIAS)
        if agent == "indexer" or task_type == "embedding":
            return RouteDecision(OLLAMA_ALIAS, SONNET_ALIAS)
        if agent == "designer":
            return RouteDecision(SONNET_ALIAS, OPUS_ALIAS)
        if agent == "devops":
            return RouteDecision(SONNET_ALIAS, OLLAMA_ALIAS)
        if agent == "tester":
            return RouteDecision(SONNET_ALIAS, OLLAMA_ALIAS)
        if agent == "coder":
            if task_type == "scaffold":
                return RouteDecision(OLLAMA_ALIAS, SONNET_ALIAS)
            if task_type in ("refactor", "architectural"):
                return RouteDecision(OPUS_ALIAS, SONNET_ALIAS)
            return RouteDecision(SONNET_ALIAS, OPUS_ALIAS)
        return RouteDecision(SONNET_ALIAS, OPUS_ALIAS)

    def get_client(self, model_alias: str, *, agent: str = "") -> ClaudeClient | OllamaClient:
        if model_alias == OLLAMA_ALIAS:
            if agent == "indexer" and self._ollama_embed.healthy():
                return self._ollama_embed
            return self._ollama_coder
        client = self._clients.get(model_alias)
        if client is None:
            return self._claude_sonnet
        return client

    def route(self, request: RouteRequest) -> ClaudeClient | OllamaClient:
        """Pick the best available client for *request* (primary with health check)."""
        decision = self.decide(request)
        agent = request.agent.lower()
        primary = self.get_client(decision.primary, agent=agent)
        if primary.healthy():
            return primary
        if decision.fallback:
            fallback = self.get_client(decision.fallback, agent=agent)
            if fallback.healthy():
                return fallback
        if self._claude_sonnet.healthy():
            return self._claude_sonnet
        if self._ollama_coder.healthy():
            return self._ollama_coder
        return primary

    async def complete(
        self,
        request: RouteRequest,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Complete a prompt with automatic failover to fallback model."""
        decision = self.decide(request)
        errors: list[str] = []

        agent = request.agent.lower()
        for alias in (decision.primary, decision.fallback):
            if alias is None:
                continue
            client = self.get_client(alias, agent=agent)
            if not client.healthy():
                errors.append(f"{alias}: unhealthy")
                continue
            try:
                response = await client.complete(
                    messages,
                    system=system,
                    max_tokens=max_tokens,
                )
                await self._record_usage(request.agent, response)
                return response
            except (LLMProviderError, LLMError) as exc:
                errors.append(f"{alias}: {exc}")

        raise LLMProviderError(
            f"All LLM providers failed for {request.agent}/{request.task_type}: {'; '.join(errors)}"
        )

    async def _record_usage(self, agent: str, response: LLMResponse) -> None:
        if self._event_bus is not None and self._session_id is not None:
            await self._event_bus.publish(
                Event(
                    type=EventType.LLM_CALL,
                    session_id=self._session_id,
                    payload={
                        "agent": agent,
                        "model": response.model,
                        "provider": response.provider,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                )
            )
        elif self.cost_tracker is not None:
            self.cost_tracker.record_response(agent, response)
