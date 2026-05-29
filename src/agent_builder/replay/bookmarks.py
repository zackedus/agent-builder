"""Auto-bookmarks for interesting replay moments."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.core.event_bus import Event, EventType
from agent_builder.llm.cost_tracker import estimate_cost

COST_MILESTONES_USD = (1.0, 5.0, 10.0)


@dataclass(frozen=True)
class ReplayBookmark:
    position: int
    label: str
    category: str


def compute_bookmarks(events: list[Event]) -> list[ReplayBookmark]:
    """Return sorted bookmarks for jump-to navigation."""
    bookmarks: list[ReplayBookmark] = []
    cumulative = 0.0
    seen_cost: set[float] = set()

    for index, event in enumerate(events):
        pos = index + 1
        if event.type == EventType.TASK_FAILED:
            task_id = event.payload.get("task_id", "?")
            bookmarks.append(
                ReplayBookmark(pos, f"Failed {task_id}", "failure"),
            )
        elif event.type == EventType.TASK_BLOCKED:
            task_id = event.payload.get("task_id", "?")
            bookmarks.append(
                ReplayBookmark(pos, f"Blocked {task_id}", "blocker"),
            )
        elif event.type == EventType.STATE_CHANGED:
            to_state = event.payload.get("to", "")
            if to_state in ("DONE", "FAILED"):
                bookmarks.append(
                    ReplayBookmark(pos, f"State → {to_state}", "milestone"),
                )
        elif event.type == EventType.TASK_COMPLETED:
            task_id = event.payload.get("task_id", "?")
            bookmarks.append(
                ReplayBookmark(pos, f"Completed {task_id}", "milestone"),
            )
        elif event.type == EventType.LLM_CALL:
            model = str(event.payload.get("model", "ollama"))
            cost = estimate_cost(
                model,
                int(event.payload.get("input_tokens", 0)),
                int(event.payload.get("output_tokens", 0)),
            )
            cumulative += cost
            for milestone in COST_MILESTONES_USD:
                if cumulative >= milestone and milestone not in seen_cost:
                    seen_cost.add(milestone)
                    bookmarks.append(
                        ReplayBookmark(
                            pos,
                            f"Cost ≥ ${milestone:.0f}",
                            "cost",
                        ),
                    )

    return sorted(bookmarks, key=lambda b: b.position)
