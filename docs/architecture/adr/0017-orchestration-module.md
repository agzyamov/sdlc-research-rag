# ADR-0017: Separate `orchestration` module for Dagster

- Status: Accepted (2026-11-15). Refines ADR-0016.
- Modules: new `orchestration` (layer 2, below `app | cli`); `ingestion` and `extraction` become plain-function modules

## Context
Fact extraction must run in the Dagster pipeline after each paper is indexed. The Dagster assets lived in `ingestion`, but the module view keeps the application siblings `ingestion`, `extraction` and `generation` independent. Wiring extraction into the pipeline would therefore violate the import contract.

## Decision
A new **`orchestration`** module holds all Dagster assets, schedules and the code location (`sdlcrag.orchestration.definitions`). It composes `ingestion`, `extraction`, `access` and `indexing`. It sits in its own layer **below `app | cli`**, because `cli` drives it (`sdlcrag ingest|update|extract` materialize assets in-process), and above the application layer.

## Alternatives
- Put Dagster in `cli` (widen it to "entry points"): smaller, but mixes two kinds of entry point.
- Move `extraction` below `ingestion`: no new module, but couples ingestion to LLM extraction.

## Consequences
+ Orchestration is a composition concern with one home; domain and application modules stay framework-free and unit-testable.
− One more module in the module view and the import-linter contract.
