# AGENTS.md

## AI Development Team System

This project uses a multi-agent software development workflow.

Agents must act like a coordinated IT development team, not isolated code generators.

## Core Rule

No agent may implement code before understanding:
1. The task brief.
2. Existing architecture.
3. Related modules.
4. Existing similar features.
5. Integration impact.
6. Testing requirement.
7. Risk level.

## Communication Rule

Agents communicate through shared project files:

- .cursor/team/task_board.md
- .cursor/team/tasks/
- .cursor/team/handoffs/
- .cursor/team/reviews/
- .cursor/team/decisions/
- .cursor/memory/feature_registry.json
- docs/module_map.md
- docs/architecture.md

Agents must write short structured handoffs after completing work.

## Chain of Responsibility

1. Orchestrator receives task.
2. Product Manager clarifies requirement.
3. Business Analyst defines business rules and edge cases.
4. Logic & Algorithm Engineer defines calculation, algorithm, data flow, and efficiency strategy.
5. Solution Architect defines implementation structure.
6. Engineering agents implement.
7. QA tests.
8. Security reviews.
9. Code Reviewer checks consistency.
10. Documentation Engineer updates docs.

## Non-Negotiable Rules

- Never create duplicate modules, services, routes, schemas, utilities, or components.
- Never invent business rules.
- Never change database schema without migration plan.
- Never change API contract without checking consumers.
- Never hardcode secrets.
- Never skip error handling for risky operations.
- Never mark task done without test/check summary.
- Never rewrite unrelated files.
- Never perform large refactor during bug fix unless explicitly requested.

## Veto Power

The following agents may block completion:

- Solution Architect: architecture violation.
- Logic & Algorithm Engineer: wrong calculation, inefficient algorithm, unsafe rounding, fake formula, or bad data-processing design.
- Security Engineer: security risk.
- QA Engineer: broken acceptance criteria.
- Code Reviewer: duplicate or unsafe implementation.
- Database Engineer: unsafe schema or migration.

## Done Criteria

A task is not done until:
1. Implementation is complete.
2. Relevant checks are run or explicitly documented.
3. Risks are documented.
4. Handoff is written.
5. Documentation is updated if behavior changed.
