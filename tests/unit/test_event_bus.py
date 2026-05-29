import asyncio
from pathlib import Path

import pytest

from agent_builder.core.event_bus import PERSISTED_EVENT_TYPES, Event, EventBus, EventType
from agent_builder.core.events_store import EventsStore


@pytest.mark.asyncio
async def test_publish_dispatches_to_subscriber() -> None:
    bus = EventBus()
    received: list[Event] = []

    def on_started(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.TASK_STARTED, on_started)
    event = Event(
        type=EventType.TASK_STARTED,
        session_id="sess-1",
        payload={"task_id": "T1.1", "agent": "coder"},
    )
    await bus.publish(event)

    assert len(received) == 1
    assert received[0].payload["task_id"] == "T1.1"
    assert bus.history()[-1] is event


@pytest.mark.asyncio
async def test_publish_dispatches_async_subscriber() -> None:
    bus = EventBus()
    received: list[str] = []

    async def on_llm(event: Event) -> None:
        received.append(event.payload["model"])

    bus.subscribe(EventType.LLM_CALL, on_llm)
    await bus.publish(
        Event(
            type=EventType.LLM_CALL,
            session_id="sess-1",
            payload={"model": "claude-sonnet"},
        )
    )
    assert received == ["claude-sonnet"]


@pytest.mark.asyncio
async def test_subscribe_all_receives_every_event() -> None:
    bus = EventBus()
    types: list[EventType] = []

    def on_any(event: Event) -> None:
        types.append(event.type)

    bus.subscribe_all(on_any)
    await bus.publish(Event(type=EventType.TASK_STARTED, session_id="s"))
    await bus.publish(Event(type=EventType.COST_UPDATED, session_id="s"))
    assert types == [EventType.TASK_STARTED, EventType.COST_UPDATED]


def test_history_trims_to_max() -> None:
    bus = EventBus(max_history=3)

    async def run() -> None:
        for index in range(5):
            await bus.publish(
                Event(
                    type=EventType.AGENT_LOG,
                    session_id="s",
                    payload={"index": index},
                )
            )

    asyncio.run(run())
    history = bus.history()
    assert len(history) == 3
    assert history[0].payload["index"] == 2


@pytest.mark.asyncio
async def test_publish_persists_critical_events_only(tmp_path: Path) -> None:
    store = EventsStore(tmp_path / "events.jsonl")
    bus = EventBus(events_store=store)

    await bus.publish(Event(type=EventType.TASK_STARTED, session_id="s", payload={"task_id": "T1"}))
    await bus.publish(Event(type=EventType.AGENT_LOG, session_id="s", payload={"message": "hello"}))
    await bus.publish(
        Event(type=EventType.TASK_COMPLETED, session_id="s", payload={"task_id": "T1"})
    )

    loaded = store.load_all()
    assert len(loaded) == 2
    assert loaded[0].type == EventType.TASK_STARTED
    assert loaded[1].type == EventType.TASK_COMPLETED


def test_persisted_event_types_include_state_changed() -> None:
    assert EventType.STATE_CHANGED in PERSISTED_EVENT_TYPES
    assert EventType.AGENT_LOG not in PERSISTED_EVENT_TYPES
