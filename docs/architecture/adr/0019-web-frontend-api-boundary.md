# ADR-0019: React web front end, `api` module, and the Python/TypeScript boundary

- Status: Accepted (2026-11-16). Supersedes the Streamlit UI (`app` module).
- Modules: new `api` (presentation layer, sibling of `cli`); `app` removed; `visualization` narrowed to chart series and graph data; new `web/` tree (TypeScript, outside the Python package).

## Context
The Streamlit UI was a basic chat with expanders for sources. The user chose assistant-ui (streaming chat with source parts) and moved all pages to a web front end: chat, research landscape, knowledge graph and evaluation. The retrieval and AI stack is Python-only (Docling, LangChain/LangGraph, embeddings, reranker, DeepEval, Dagster, neo4j-graphrag). The best-of-breed UI libraries are TypeScript-only (assistant-ui, shadcn/ui, Sigma.js). Two languages are therefore unavoidable, and the boundary between them must be explicit and enforced, because coding agents write most new code.

## Decision
**C&C:** a browser SPA and the FastAPI server are separate components. They connect through HTTP JSON request/reply (`/api/landscape`, `/api/graph`, `/api/eval`, `/api/principals`) and an HTTP stream (`/api/chat`, assistant-ui data-stream protocol via `assistant-stream`: text deltas, then one source part per cited chunk).

**Module view:** `sdlcrag.api` (FastAPI + assistant-stream) is a presentation module beside `cli`. `web/` is a separate module tree with its own rules (`web/.dependency-cruiser.cjs`):
- pages use components and `lib/api`
- vendored registry components (`components/ui`, `components/assistant-ui`) use only `lib/utils`
- only `lib/api` touches the generated client and axios
- nothing imports from outside `web/`

**Contract:** the only shared artifact is `contracts/openapi.json`, generated from the Pydantic response models (`tools/gen_api_contract.py`). **orval** generates TanStack Query hooks over axios from it into `web/src/lib/api/generated.ts`. A change to an API model therefore breaks `tsc` on the web side until the client is regenerated and the pages fixed.

**Allocation:** the web app runs in the browser. It is built by Vite into static files; in development the Vite server proxies `/api` to uvicorn (`uv run sdlcrag serve`). `src/` maps to the Python process, `web/` to the browser.

**Identity (demo):** the selected demo user travels in `X-Demo-User` and must be one of `data/corpus.yaml` principals. This is a user switcher, not authentication; a deployment derives the principal from a verified token (OIDC proxy) instead. Per-user queries include the user in the TanStack Query key, so cached data never crosses users.

**Guardrails:**

| Guardrail | Where enforced |
|---|---|
| Python only in `src/`, `tools/`, `tests/`; TypeScript only in `web/` | pre-commit hooks, pytest (`test_languages_stay_on_their_side_of_the_boundary`) |
| Contract file fresh | pytest, pre-commit, CI quality-gates job |
| Generated client fresh | `pnpm check:api`: pre-commit, CI web job |
| No hand-written HTTP; API only via `@/lib/api` | dependency-cruiser rules and oxlint `no-restricted-globals` (`fetch`) |
| Web module rules | dependency-cruiser |
| Agent instructions | `CLAUDE.md`, section "Python / TypeScript boundary" |

**Tooling on TypeScript 7:** TypeScript 7.0 ships no JavaScript compiler API (a new API arrives in 7.1). The chosen tools do not depend on it:
- orval generates from templates.
- dependency-cruiser runs with its swc parser (`@swc/core`).
- oxlint is native.

Toolchain versions are not downgraded to fit a tool.

## Alternatives
- **Python-only UI** (Reflex, Gradio, NiceGUI, or keeping Streamlit): one language, but no assistant-ui or Sigma.js and less control over design and accessibility. Reflex still compiles to React, just hidden.
- **openapi-typescript + openapi-fetch**: needs the TypeScript compiler API (open issue openapi-ts/openapi-typescript#2841), so it would only run with a private TypeScript 5/6. Revisit when it supports the TypeScript 7.1 API; the generator sits behind one script (`gen:api`).
- **@hey-api/openapi-ts**: the same compiler-API dependency.
- **Hand-written TypeScript types**: no generator, but the contract can drift silently. That is the failure the boundary exists to prevent.
- **LangGraph Server + assistant-ui's LangGraph runtime**: less glue, but self-hosted production use needs a LangSmith license.
- **BI tools for the dashboards** (Superset, Metabase, Evidence): they would need a second copy of the OpenFGA access rules as row-level security, and Metabase is AGPL.

## Consequences
+ Best-of-breed UI with streaming, citations as source chips, and a WebGL graph that scales past thousands of nodes.
+ The boundary is mechanical, not a convention: a mismatch on either side fails pre-commit and CI.
− Two toolchains (uv and pnpm) and two CI jobs.
− The generated client follows orval's conventions (one hook per endpoint).
− Chat is single-turn: the API answers the latest user message. Multi-turn is an open product decision.

## Amendment (2026-11-16): drill-through
The impeccable critique scored the first landscape and graph pages 15/40: charts made claims you could not check, colours meant different things per tab, and dark-mode graph labels were unreadable. Changes:
- **Drill-through:** `GET /api/papers` (readable papers having every given fact, or one paper) and the same filters on `/api/landscape` (cross-filtering). All filtering runs server-side over the OpenFGA-readable set; the web app only sends the selection.
- **Bar lists instead of a donut and Recharts bars:** Tremor BarList (vendored, Apache-2.0) renders rows as native buttons, so every phase and fact is keyboard- and screen-reader-reachable. Recharts bars are SVG shapes that cannot take focus, so Recharts was removed. The phase chart counts papers per phase in lifecycle order and keeps zero rows (honest absence).
- **One phase colour everywhere:** phase N wears categorical slot N on the strip, the graph and the paper panel. Other graph node types use neutral steps.
- **Sigma colours:** theme tokens are `oklch()`, which Sigma's WebGL renderer cannot parse. culori converts them to `rgb()/rgba()`, re-read on theme change. The layout is deterministic (circular seed + ForceAtlas2).
- **URL state (nuqs):** tab, demo user and selection live in the URL, so a view can be shared.

## Amendment 2 (2026-11-16): evidence and access scope
The second critique scored 23/40. Its P0: tags could not be verified.
- **Evidence:** extraction returns a verbatim abstract quote per fact (`FACTS_FORMAT` 3). Python keeps a quote only if it really occurs in the title or abstract (whitespace- and case-insensitive); a paraphrase is dropped rather than shown as evidence. Quotes are stored on the Neo4j edges and returned by `/api/papers` (`evidence`, `published`). In the 20-paper corpus, 91 of 92 facts have a verified quote.
- **Access scope:** `/api/landscape` returns `corpus_papers`, so a public user sees "11 of 20 papers … 9 internal-only". The count is computed server-side; restricted titles and facts never leave the API.
- **No blanking:** TanStack Query's `placeholderData` keeps the previous result while a selection loads, but only for the same user (`asUser`), so one user's data never flashes on another's screen.
- **Graph:** sigma's built-in SDF node shapes make node type independent of shade (round 3: paper circle, phase square, technique triangle, model diamond, benchmark rectangle; one map in `pages/shapes.tsx` shared with the legend and the panel chips). Phase labels are always on. A Find combobox (shadcn Popover + Command/cmdk) gives a keyboard path, react-sigma's `ZoomControl` adds zoom and fit, and the legend states how many papers have no extracted facts.
