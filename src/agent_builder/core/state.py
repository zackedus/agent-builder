"""Pydantic models for session, plan, and task state."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer

Complexity = Literal["small", "medium", "large"]


class OrchestratorState(StrEnum):
    """FSM states for the orchestrator (ARCHITECTURE.md §5)."""

    IDLE = "IDLE"
    PLANNING = "PLANNING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PLAN_APPROVAL = "PLAN_APPROVAL"
    TASK_LOOP = "TASK_LOOP"
    INDEXING = "INDEXING"
    DESIGNING = "DESIGNING"
    CODING = "CODING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    INTEGRATION_TEST = "INTEGRATION_TEST"
    DEPLOYING = "DEPLOYING"
    DONE = "DONE"
    FAILED = "FAILED"


TERMINAL_ORCHESTRATOR_STATES = frozenset({OrchestratorState.DONE, OrchestratorState.FAILED})


class TaskStatus(StrEnum):
    """Kanban / dashboard task status (ARCHITECTURE.md §15.5)."""

    PENDING = "pending"
    BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"
    RUNNING = "running"
    BLOCKED_RETRY_EXCEEDED = "blocked_retry_exceeded"
    BLOCKED_NEEDS_INPUT = "blocked_needs_input"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED_UNRECOVERABLE = "failed_unrecoverable"


class SessionMetrics(BaseModel):
    total_llm_calls: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: int = 0


class SessionState(BaseModel):
    """Persisted orchestrator session (`state.json`)."""

    model_config = ConfigDict(use_enum_values=True)

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_state: OrchestratorState = OrchestratorState.IDLE
    current_task: str | None = None
    user_prompt: str = ""
    retry_count: dict[str, int] = Field(default_factory=dict)
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)
    tasks: list[TaskNode] = Field(default_factory=list)

    @field_serializer("started_at")
    @classmethod
    def serialize_started_at(cls, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()

    def is_terminal(self) -> bool:
        return self.current_state in TERMINAL_ORCHESTRATOR_STATES

    def get_task_retry_count(self, task_id: str) -> int:
        return self.retry_count.get(task_id, 0)

    def increment_task_retry(self, task_id: str) -> int:
        count = self.get_task_retry_count(task_id) + 1
        self.retry_count[task_id] = count
        return count


class TaskNode(BaseModel):
    """Runtime task node for dashboard and dependency graph."""

    id: str
    title: str
    assigned_agent: str
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)
    estimated_complexity: Complexity = "medium"
    retry_count: int = 0
    on_critical_path: bool = False
    blocker_reason: str | None = None

    model_config = ConfigDict(use_enum_values=True)


class TechStack(BaseModel):
    model_config = ConfigDict(extra="allow")

    gui: str | None = None
    storage: str | None = None
    charts: str | None = None


class PlanTask(BaseModel):
    id: str
    title: str
    type: str
    depends_on: list[str] = Field(default_factory=list)
    files_affected: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class PlanMilestone(BaseModel):
    id: str
    name: str
    tasks: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Planner output (`plan.json`)."""

    project_name: str
    description: str
    tech_stack: TechStack = Field(default_factory=TechStack)
    milestones: list[PlanMilestone] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)
    estimated_complexity: Complexity = "medium"
    risks: list[str] = Field(default_factory=list)


_COMPLEXITY_WEIGHT: dict[Complexity, int] = {"small": 1, "medium": 2, "large": 3}


def compute_critical_path(tasks: list[TaskNode]) -> set[str]:
    """Return task IDs on the longest weighted dependency path."""
    if not tasks:
        return set()

    by_id = {t.id: t for t in tasks}
    memo: dict[str, tuple[int, list[str]]] = {}

    def longest_from(task_id: str, visiting: set[str]) -> tuple[int, list[str]]:
        if task_id in memo:
            return memo[task_id]
        if task_id in visiting:
            return 0, []
        visiting.add(task_id)
        node = by_id.get(task_id)
        if node is None:
            return 0, []

        weight = _COMPLEXITY_WEIGHT.get(node.estimated_complexity, 1)
        best_cost = weight
        best_path = [task_id]

        for dep_id in node.depends_on:
            if dep_id not in by_id:
                continue
            dep_cost, dep_path = longest_from(dep_id, visiting)
            total = dep_cost + weight
            if total > best_cost:
                best_cost = total
                best_path = dep_path + [task_id]

        visiting.remove(task_id)
        memo[task_id] = (best_cost, best_path)
        return best_cost, best_path

    global_best: list[str] = []
    global_cost = -1
    for task in tasks:
        cost, path = longest_from(task.id, set())
        if cost > global_cost:
            global_cost = cost
            global_best = path

    return set(global_best)


def apply_critical_path_flags(tasks: list[TaskNode]) -> list[TaskNode]:
    """Return tasks with ``on_critical_path`` set from ``compute_critical_path``."""
    critical = compute_critical_path(tasks)
    return [t.model_copy(update={"on_critical_path": t.id in critical}) for t in tasks]


def session_state_from_json(data: str) -> SessionState:
    return SessionState.model_validate_json(data)


def session_state_to_json(state: SessionState, *, indent: int = 2) -> str:
    return state.model_dump_json(indent=indent)


def plan_from_json(data: str) -> Plan:
    return Plan.model_validate_json(data)


def plan_to_json(plan: Plan, *, indent: int = 2) -> str:
    return plan.model_dump_json(indent=indent)
