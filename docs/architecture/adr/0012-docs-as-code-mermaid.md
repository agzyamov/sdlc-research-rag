# ADR-0012: Diagrams as code with Mermaid, generated from source where possible

- Status: Accepted (2026-11-15)

## Context
Architecture docs must carry diagrams and stay accurate as the app evolves. Hand-drawn images rot.

## Decision
- **Mermaid** (MIT) for all diagrams, inline in Markdown. Rendered natively by GitHub and most IDEs, diffable, reviewable in PRs.
- **Generated diagrams** (`tools/gen_diagrams.py`):
  - module dependency graph from the actual imports via **grimp** (the engine behind import-linter)
  - RAG graph from LangGraph's built-in `draw_mermaid()`
- **Freshness gates**: a pytest check (`--check` mode), a pre-commit hook, and CI.
- **Syntax validation**: `@mermaid-js/mermaid-cli` renders every block in CI (`tools/check_mermaid.sh`).

## Alternatives
- Structurizr DSL (C4-centric, needs a renderer/server; our documentation method is Views and Beyond, not C4)
- D2 (prettier layouts, but GitHub does not render it natively)
- PlantUML (needs Java/server)
- draw.io (binary-ish XML, not generated)

## Consequences
+ Zero-friction rendering; intended (hand-written) and implemented (generated) diagrams sit side by side, which is a V&B conformance check.
− Mermaid layout control is limited. D2 can be added later for presentation-grade exports, without changing the source-of-truth rule.
