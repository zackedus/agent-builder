"""In-memory pub/sub event bus for orchestrator and dashboard."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agent_builder.core.events_store import EventsStore

EventCallback = Callable[["Event"], Awaitable[None] | None]


class EventType(StrEnum):
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    AGENT_LOG = "agent_log"
    LLM_CALL = "llm_call"
    STATE_CHANGED = "state_changed"
    COST_UPDATED = "cost_updated"


PERSISTED_EVENT_TYPES = frozenset(
    {
        EventType.TASK_STARTED,
        EventType.TASK_COMPLETED,
        EventType.TASK_FAILED,
        EventType.STATE_CHANGED,
        EventType.LLM_CALL,
        EventType.COST_UPDATED,
    }
)


class Event(BaseModel):
    """Domain event published on the bus and optionally persisted to ``events.jsonl``."""

    type: EventType
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_jsonl_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ts": self.timestamp.astimezone(UTC).isoformat(),
            "type": self.type.value,
            "session_id": self.session_id,
            **self.payload,
        }
        return data

    def to_jsonl_line(self) -> str:
        import json

        return json.dumps(self.to_jsonl_dict(), ensure_ascii=False)

    @classmethod
    def from_jsonl_dict(cls, data: dict[str, Any]) -> Event:
        raw_type = data.pop("type")
        ts_raw = data.pop("ts", None)
        session_id = data.pop("session_id", "")
        payload = dict(data)
        timestamp = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(UTC)
        return cls(
            type=EventType(raw_type),
            session_id=session_id,
            timestamp=timestamp,
            payload=payload,
        )


class EventBus:
    """Async pub/sub bus with in-memory history and optional JSONL persistence."""

    def __init__(
        self,
        *,
        max_history: int = 10_000,
        events_store: EventsStore | None = None,  # noqa: F821
    ) -> None:
        self._subscribers: dict[EventType, list[EventCallback]] = {}
        self._wildcard_subscribers: list[EventCallback] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._events_store = events_store

    def subscribe(self, event_type: EventType, callback: EventCallback) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def subscribe_all(self, callback: EventCallback) -> None:
        self._wildcard_subscribers.append(callback)

    def history(self) -> list[Event]:
        return list(self._history)

    async def publish(self, event: Event) -> None:
        self._append_history(event)
        if self._events_store is not None and event.type in PERSISTED_EVENT_TYPES:
            self._events_store.append(event)
        await self._dispatch(event)

    def publish_sync(self, event: Event) -> None:
        """Publish from synchronous code (runs async dispatch in a new loop if needed)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.publish(event))
            return
        loop.create_task(self.publish(event))

    def _append_history(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    async def _dispatch(self, event: Event) -> None:
        callbacks = list(self._wildcard_subscribers)
        callbacks.extend(self._subscribers.get(event.type, []))
        for callback in callbacks:
            await self._invoke(callback, event)

    async def _invoke(self, callback: EventCallback, event: Event) -> None:
        result = callback(event)
        if inspect.isawaitable(result):
            await result
