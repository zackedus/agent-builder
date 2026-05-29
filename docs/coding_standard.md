# Coding Standard

## General

- Follow existing project conventions.
- Keep code small and readable.
- Prefer explicit names.
- Avoid duplicate utilities.
- Avoid hidden side effects.
- Avoid unrelated refactors.

## Naming

Use the naming convention already present in the project.

## Errors

All risky operations must include:
- validation
- error handling
- user-safe error message if UI-facing
- developer log if useful

## Logic / Calculation

- Keep raw numeric values separate from formatted display values.
- Do not round too early.
- Do not invent formulas.
- Keep logic testable.
- Prefer pure functions for calculations.
- Define units and precision clearly.

## Testing

Every meaningful feature should include or update:
- unit test
- integration test
- UI/component test
- API test

depending on project type.
