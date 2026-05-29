from agent_builder.agents.task_selection import next_executable_task, order_plan_tasks
from agent_builder.core.state import Plan, PlanTask


def test_order_plan_tasks_respects_dependencies() -> None:
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(id="T2", title="B", type="logic", depends_on=["T1"]),
            PlanTask(id="T1", title="A", type="scaffold"),
        ],
    )
    ordered = order_plan_tasks(plan)
    assert [t.id for t in ordered] == ["T1", "T2"]


def test_next_executable_task_skips_completed() -> None:
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(id="T1", title="A", type="scaffold"),
            PlanTask(id="T2", title="B", type="logic", depends_on=["T1"]),
        ],
    )
    nxt = next_executable_task(plan, ["T1"])
    assert nxt is not None
    assert nxt.id == "T2"

    done = next_executable_task(plan, ["T1", "T2"])
    assert done is None
