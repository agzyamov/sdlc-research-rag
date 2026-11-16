# Architecture documentation: SDLC Research RAG

Documented with the SEI **Views and Beyond** (V&B) approach: an architecture is documented as a set of *views*, one per relevant viewpoint, plus the information that goes *beyond* the views (rationale, mapping between views, and quality attributes).

## Documentation roadmap

| # | Document | Viewtype / style | Primary stakeholders | Answers |
|---|---|---|---|---|
| 1 | [01-module-view.md](01-module-view.md) | Module: decomposition, uses, layered | developers, AI assistants | *Where does this code belong? What may depend on what?* (**quality gate**) |
| 2 | [02-cc-view.md](02-cc-view.md) | Component & Connector: pipe-and-filter, client-server | developers, reviewers | *What happens at runtime when we ingest, ask, and evaluate?* |
| 3 | [03-allocation-view.md](03-allocation-view.md) | Allocation: deployment, implementation | operators, developers | *What runs where? Which module lives in which path?* |
| 4 | [04-quality-attributes.md](04-quality-attributes.md) | Beyond views: QA scenarios | architect, evaluators | *What qualities matter, and how are they measured?* |
| 5 | [adr/](adr/) | Beyond views: rationale | everyone | *Why was each technology chosen?* |
| 6 | [generated/](generated/) | As-implemented diagrams, generated from code | architect, reviewers | *Does the code still match the intended views?* |

## Diagrams as code (ADR-0012)
- **Every view has diagrams**, written in **Mermaid** inside the Markdown. GitHub renders them natively; no binary images.
- **As-implemented diagrams are generated from the code** by `tools/gen_diagrams.py`:
  - `generated/module-dependencies.md`: the real module uses-graph (grimp), to compare with the intended Module View
  - `generated/rag-graph.md`: the LangGraph state machine, via `draw_mermaid()`
- **Kept up to date automatically:**
  - `pytest` fails when the generated diagrams are stale or the views disagree with the code (`tests/unit/test_architecture.py`).
  - pre-commit regenerates the diagrams and validates Mermaid syntax.
  - CI runs the same checks plus `tools/check_mermaid.sh` (mermaid-cli renders every block).
- **Rule:** a change that alters runtime behavior, deployment, or module uses also updates the matching hand-written view (02/03/01) in the same commit.

## Change policy
- **Module View = quality gate.** New code goes into an existing module whose responsibility fits. If none fits, the change is an *architectural decision*: escalate, update the Module View plus the import-linter contract, and record an ADR.
- Views stay consistent with each other. The implementation mapping in the allocation view must list every package in the module view, and vice versa (checked by `tests/unit/test_architecture.py`).

## View template (V&B)
Each view document contains:
1. **Primary presentation**: diagram or table
2. **Element catalog**: elements, responsibilities, interfaces, behavior
3. **Context**: what lies outside the view's scope
4. **Variability guide**: planned extension points
5. **Rationale**: links to ADRs
