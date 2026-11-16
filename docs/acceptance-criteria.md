# Acceptance criteria

User-facing acceptance criteria, each covered by a Playwright test in [`web/e2e/`](../web/e2e) (ADR-0020). Test titles start with the criterion ID, so `pnpm -C web e2e -g "AC-5"` runs one criterion.

System quality scenarios (faithfulness, retrieval quality, modifiability, cost) are not browser behavior. They are QA-1…QA-9 in [04-quality-attributes.md](architecture/04-quality-attributes.md), covered by pytest and DeepEval.

| ID | Criterion | Test | Modes |
|---|---|---|---|
| AC-1 | Chat: a question streams an answer with inline `[n]` citations and source chips linking to arXiv (paper, section, page) | `chat.spec.ts` | mocked; live with `E2E_LLM=1` |
| AC-2 | Chat access control: a public user (alice) never gets a restricted paper as a source | `chat.spec.ts` | mocked; live with `E2E_LLM=1` |
| AC-3 | Switching the demo user changes what you see and resets the chat thread | `chat.spec.ts` | mocked; live with `E2E_LLM=1` |
| AC-4 | Landscape shows the readable-paper total and all 8 phases in lifecycle order, zeros included | `landscape.spec.ts` | mocked, live |
| AC-5 | Clicking a phase or fact opens the paper panel (title, arXiv link, license badge) and cross-filters the lists | `landscape.spec.ts` | mocked, live |
| AC-6 | Fact chips pivot the selection; filter chips remove filters; Esc and Close clear the panel | `landscape.spec.ts` | mocked, live |
| AC-7 | Access control in the landscape and panel: alice only sees open-licensed papers, also via a direct paper URL | `landscape.spec.ts` | mocked, **live (proof)** |
| AC-8 | Graph: clicking a node opens its papers and focuses its neighborhood; clicking the background clears | `graph.spec.ts` | mocked, live |
| AC-9 | Any view is shareable: opening its URL restores tab, user and selection | `landscape.spec.ts` | mocked, live |
| AC-10 | The evaluation page shows summary metrics against targets plus per-question rows; empty state before the first run | `evaluation.spec.ts` | mocked; live (empty state: mocked only) |
| AC-11 | Keyboard: phase rows, fact rows and panel controls work with Tab and Enter, with a visible focus ring | `landscape.spec.ts` | mocked, live |
| AC-12 | Accessibility: no WCAG 2.1 A/AA violations on any tab, light and dark (axe-core) | `a11y.spec.ts` | mocked, live |
| AC-14 | Errors: when the API fails, pages show a plain message and "Try again" recovers | `errors.spec.ts` | mocked (failure injected) |
| AC-15 | Every tag on a paper shows the verbatim abstract quote that supports it, or says none was found; papers show their submission date | `evidence.spec.ts` | mocked, live |
| AC-16 | Changing the selection keeps the page and keyboard focus in place while it loads (no full-page skeleton) | `evidence.spec.ts` | mocked (slowed), live |
| AC-17 | The graph works from the keyboard: searching a node selects it; zoom and fit controls exist; node types differ by shape | `evidence.spec.ts` | mocked, live |
| AC-18 | A public user sees how many papers exist beyond their access (count only, never which) | `evidence.spec.ts` | mocked, live |
| AC-19 | Every bar row announces its count to assistive tech; card titles are headings inside a `<main>` landmark | `accessibility-flow.spec.ts` | mocked, live |
| AC-20 | A paper groups its tags by type with visible labels; the quotes follow the chip order and mark a quote shared by several tags | `accessibility-flow.spec.ts` | mocked, live |
| AC-21 | A selected graph node is centred beside the panel, not under it | `accessibility-flow.spec.ts` | mocked, live |
| AC-22 | Keyboard flow: "Jump to papers" moves focus to the panel, Esc returns focus to the selected row, the Find input is named | `accessibility-flow.spec.ts` | mocked, live |
| AC-23 | Fact lists never truncate silently: every item, or "Top 10 of N" with "Show all N" | `honesty.spec.ts` | mocked, live |
| AC-24 | The selected graph node is enlarged and labelled on a backdrop; its neighbours are labelled; the overview labels facts and phases, paper titles on hover | `honesty.spec.ts` | mocked, live |
| AC-25 | Every count stays visible inside its card, even next to a long label with the panel open; truncated labels show their full name on hover | `honesty.spec.ts` | mocked, live |
| AC-26 | Every card caption names the full scope it counts over (all active filters); an empty list says "None", never "All 0" | `honesty.spec.ts` | mocked, live |
| AC-27 | Focus indicators (bars, chips, buttons, links, demo-user select, tabs, tab panel) are a solid 2px outline with at least 3:1 contrast in light and dark, and look different from a selected row (inset ring) | `focus.spec.ts` | mocked, live |
| AC-28 | Graph Find matches whole words; typing a phase name and pressing Enter selects that phase, not a fuzzy paper match | `focus.spec.ts` | mocked, live |
| AC-29 | With combined filters the graph highlights exactly the papers the panel lists (one shared query), and every selected phase or fact node | `honesty.spec.ts` | mocked, live |
| AC-30 | A selection with nothing the user may read (e.g. after switching from bob to alice) dims the whole graph and says "Nothing <user> may read matches this selection" | `honesty.spec.ts` | mocked, live |

There is no AC-13.

## Modes
- **mocked** (default, CI): `pnpm -C web e2e`. The API is stubbed by `web/e2e/support/mock-api.ts`, typed with the orval-generated contract types. It costs no LLM tokens and needs no services.
- **live**: `pnpm -C web e2e:live`. Runs against the real stack (`uv run sdlcrag serve`, Qdrant, Neo4j, OpenFGA, an ingested corpus). Only live runs prove the access-control criteria (AC-2, AC-7).
- **live + LLM**: `pnpm -C web e2e:llm`. Adds the chat criteria against the real model. It costs gateway tokens: about 3 questions per run.

The specs are data-agnostic. They assert relations (for example, the panel lists as many papers as the clicked row counts; alice's papers ⊂ bob's), so one spec serves both modes.

## Adding a criterion
A new user-facing behavior needs an AC row here and a Playwright test whose title starts with its ID, in the same commit.
