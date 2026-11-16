## What and why
<!-- What this changes and the problem it solves. Link the issue if there is one. -->

## Checklist
- [ ] The code sits in the Module View element whose responsibility covers it (`docs/architecture/01-module-view.md`); no new top-level package without a prior discussion.
- [ ] No hand-rolled code where a library or framework built-in fits; any custom code names the libraries checked (ADR-0016).
- [ ] Docs updated with the code: matching architecture view, ADR for a technology change, diagrams regenerated (`uv run python tools/gen_diagrams.py`).
- [ ] API change: contract and client regenerated (`uv run python tools/gen_api_contract.py && pnpm -C web gen:api`).
- [ ] User-facing behaviour: acceptance criterion and its Playwright spec added or updated (`docs/acceptance-criteria.md`, `web/e2e/`).
- [ ] `uv run pytest && uv run lint-imports && uv run ruff check . && uv run pyrefly check` and `pnpm -C web check && pnpm -C web build` pass.
- [ ] No papers, indexes, keys or `.env` committed.
