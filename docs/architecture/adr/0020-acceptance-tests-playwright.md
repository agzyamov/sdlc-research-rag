# ADR-0020: Acceptance tests with Playwright (mocked in CI, live locally)

- Status: Accepted (2026-11-16).
- Scope: `web/e2e/` (tests, outside `web/src`), `docs/acceptance-criteria.md`.

## Context
Every user-facing acceptance criterion must have an automated browser test. The app's behavior spans the browser (React), the API contract and server-side access control (OpenFGA), and parts of it call a paid LLM. CI has no Qdrant, Neo4j, OpenFGA or corpus, and must not spend gateway tokens.

## Decision
- **Playwright** (`@playwright/test`) runs the acceptance tests, and **axe-core** (`@axe-core/playwright`) checks WCAG 2.1 A/AA. Test titles start with the criterion ID from `docs/acceptance-criteria.md`, which maps every ID to its test.
- **One spec set, two modes:**
  - **mocked** (default, CI job `e2e`): Playwright `page.route` serves a small typed dataset (`web/e2e/support/mock-api.ts`). It reimplements access control per demo user, filters and counts, and streams chat in assistant-ui's data-stream format.
  - **live** (`E2E_LIVE=1`): the same specs run against the real stack. Chat specs are tagged `@llm` and also need `E2E_LLM=1`, because they cost tokens.
- **Specs are data-agnostic:** they assert relations, not fixture values, so they hold for any corpus.
- **Fixtures are typed** with the orval-generated contract types and type-checked by `tsc -b` (`tsconfig.e2e.json`), so an API change breaks the fixtures as well as the app.
- **Test seam:** dev builds expose the Sigma instance as `window.__sigma`, so the graph spec can click a node at its screen position. It is stripped from production builds.

## Alternatives
- **Playwright `routeFromHAR` (record and replay):** matches requests on URL and method only. Access control depends on the `X-Demo-User` header, so a recording cannot represent alice and bob.
- **MSW (Mock Service Worker):** needs the same hand-written handlers, plus a service worker in the app.
- **Live only:** would need services and a corpus provisioned in CI, plus LLM tokens per run.
- **Cypress:** a heavier runner; Playwright has a first-class axe integration and parallel workers.

## Consequences
+ Every acceptance criterion is executable in CI in about 15 seconds, with zero tokens.
+ The access-control criteria are proven against OpenFGA in live mode.
− The mocked backend duplicates a little server behavior (filters, per-user readable sets). The live mode exists to catch divergence.
− Playwright browsers are downloaded in CI (cached by the action).
