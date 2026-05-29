"""Planner agent — user prompt to plan.json."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.plan_parser import PlanParseError, parse_plan
from agent_builder.core.state import Plan
from agent_builder.llm.types import LLMMessage

PLANNER_SYSTEM = """You are the Planner agent for Agent Team Builder.
Output ONLY valid JSON matching the plan schema.
No markdown outside a single json code block.
Every task needs unique id (T1.1, T1.2), type (scaffold|logic|ui|test),
depends_on, files_affected, acceptance_criteria.
Include estimated_complexity: small|medium|large and risks array."""


class PlannerAgent(BaseAgent):
    """Translates a user prompt into a structured ``Plan`` saved as plan.json."""

    name = "planner"
    max_retries = 2

    async def execute(self, context: AgentContext) -> AgentResult:
        feedback = str(context.extra.get("feedback", ""))
        user_prompt = context.user_prompt
        if feedback:
            user_prompt = f"{user_prompt}\n\nPrevious attempt errors:\n{feedback}"

        prompt = self.load_prompt("planner", user_prompt=user_prompt)
        messages = [LLMMessage(role="user", content=prompt)]

        response = await self.complete_llm(
            context,
            messages,
            system=PLANNER_SYSTEM,
            max_tokens=8000,
            task_type="default",
        )

        try:
            plan = parse_plan(response.text)
        except PlanParseError as exc:
            return AgentResult(
                success=False,
                output=str(exc),
                data={"raw": response.text},
                last_model=response.model,
            )

        return AgentResult(
            success=False,
            output=response.text,
            data={"plan": plan, "raw": response.text},
            last_model=response.model,
        )

    def validate_result(self, result: AgentResult) -> bool:
        plan = result.data.get("plan")
        return isinstance(plan, Plan) and bool(plan.tasks)
