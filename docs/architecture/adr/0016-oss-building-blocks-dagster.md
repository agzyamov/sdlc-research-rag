# ADR-0016: OSS building blocks first; Dagster orchestrates ingestion

- Status: Accepted (2026-11-15)
- Modules: `ingestion` (Dagster assets and definitions), and every module, via the building-block map below

## Context
Hard project rule: **nothing is built from scratch that an established OSS building block already provides.** Project code is glue plus genuine business rules (corpus scope, rolling window, license policy). A review found hand-written orchestration (per-paper loop, retries, sync-state file, resume), a custom LLM factory, a custom manifest and a custom golden-set loader.

## Decision
1. **Dagster** orchestrates the corpus pipeline: assets `corpus_plan` (harvest, window, deletions) and `paper_index` (one dynamic partition per arXiv paper). Dagster provides:
   - per-paper status, retries (`RetryPolicy`) and resume (only missing or failed partitions run)
   - lineage and the UI
   - the daily schedule, plus `AutomationCondition.eager()` to index newly registered papers
   - the last-harvest cursor, kept as materialization metadata, so there's no state file

   The CLI materializes the same assets in-process against the same instance (`.dagster/`).
2. **Building-block map**, the default answer for each concern:

| Concern | Building block |
|---|---|
| Orchestration, scheduling, retries, resume | Dagster |
| arXiv harvesting (OAI-PMH paging, retries) | `oaipmh-scythe` |
| Request throttling | `pyrate-limiter` |
| PDF parsing and chunking | Docling (`langchain-docling`, `HybridChunker`) |
| Incremental indexing (content hashes, cleanup) | LangChain Indexing API (`index()` + `SQLRecordManager`) |
| Hybrid vector search | `langchain-qdrant` (dense + BM25 via FastEmbed, RRF) |
| Embeddings | `langchain-huggingface` (sentence-transformers) |
| Chat models per backend | LangChain `init_chat_model` |
| Reranking (retrieval step) | LangChain `CrossEncoderReranker` + `ContextualCompressionRetriever` |
| Authorization (access step) | OpenFGA SDK (`ListObjects`, `BatchCheck`); check Auth0's LangChain `FGARetriever` for the post-filter |
| Figure descriptions (multimodal step) | Docling picture description (OpenAI-compatible API) |
| Structured extraction (extraction step) | `with_structured_output(method="json_schema")`: schema-constrained, works through the gateway (forced tool calls are rejected by current Claude models) |
| Fact counts for charts | Cypher aggregation in Neo4j, filtered by the user's readable papers (ADR-0018) |
| Knowledge graph + name normalization | Neo4j + neo4j-graphrag `FuzzyMatchResolver` (ADR-0018). `LLMGraphTransformer` was considered and not used: the extracted facts already are the edges, and it needs forced tool calls plus a second LLM pass |
| Acceptance tests (browser) | Playwright + axe-core, route mocking (ADR-0020) |
| Evaluation data and metrics | DeepEval `EvaluationDataset` / `Golden`, metrics, `evaluate()` |
| Tracing | Langfuse LangChain callback |
| Charts, graph, UI, CLI, config | web: Tremor BarList (clickable, accessible bar lists), Sigma.js + graphology (+ graphology-layout), assistant-ui, TanStack Query, orval, nuqs (URL state), culori (colour conversion) (ADR-0019); NetworkX for graph data; Typer, pydantic-settings |

## Alternatives (orchestrator)
- Prefect 3: lighter and decorator-based, but weaker asset and lineage model.
- Airflow 3: heavyweight for a single local pipeline.
- Dagster is being acquired by Prefect (announced July 2026); both are stated to continue.

## Consequences
+ Less custom code: orchestration, state, resume and retries come from Dagster; the manifest from LangChain.
+ A UI with per-paper lineage, materialization metadata and run history (`dagster dev`).
− An extra runtime process (Dagster webserver and daemon) for schedules and automation; the CLI path needs none.
− Custom code needs a short justification naming the libraries checked (CONTRIBUTING, CLAUDE.md).
