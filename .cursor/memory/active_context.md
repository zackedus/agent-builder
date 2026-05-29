# Active Context

**Last updated:** 2026-05-29 — F4.6 E2E selesai, Fase 4 complete

## Lanjut dari sini

- **Phase:** Fase 5 — Dashboard (`dashboard/` Flet app)
- **Selesai:** Fase 4 full pipeline E2E (expense tracker mocked)
- **Prompt:** `lanjut` atau *Lanjut Fase 5 dashboard*

## File penting

| Tujuan | Path |
|--------|------|
| E2E expense | `tests/e2e/test_expense_build.py` |
| Release checks | `src/agent_builder/validation/build_output.py` |
| Example prompt | `examples/expense_tracker_prompt.txt` |

## Commands

```powershell
pytest -m "not integration" -q
pytest tests/e2e/test_expense_build.py -v
```
