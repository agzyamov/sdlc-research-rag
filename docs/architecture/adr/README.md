# Architecture Decision Records

Format: Context · Decision · Alternatives · Consequences. Status values: Proposed, Accepted, Superseded by ADR-XXXX.
The stack is chosen as **best-of-breed OSS as of November 2026** (LangChain/LangGraph and Claude were fixed upfront).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-orchestration-langchain-langgraph.md) | LangChain + LangGraph for orchestration | Accepted |
| [0002](0002-llm-anthropic-claude.md) | Anthropic Claude for generation, vision and judge | Accepted |
| [0003](0003-document-parsing-docling.md) | Docling for document parsing | Accepted |
| [0004](0004-vector-store-qdrant.md) | Qdrant as the vector store (hybrid, incremental) | Accepted |
| [0005](0005-embeddings-qwen3-bm25-hybrid.md) | Qwen3-Embedding + BM25 hybrid retrieval | Accepted |
| [0006](0006-reranker-bge-v2-m3.md) | bge-reranker-v2-m3 cross-encoder | Accepted |
| [0007](0007-authorization-openfga.md) | OpenFGA for access-control-aware RAG | Accepted |
| [0008](0008-evaluation-deepeval.md) | DeepEval for RAG evaluation | Accepted |
| [0009](0009-observability-langfuse.md) | Langfuse for tracing and eval datasets | Accepted |
| [0010](0010-dataset-sec-10k-superseded.md) | SEC 10-K filings as the corpus | Superseded by 0013 |
| [0011](0011-tooling-uv-ruff-pyrefly-import-linter.md) | uv, ruff, pyrefly, import-linter, Colima | Accepted |
| [0012](0012-docs-as-code-mermaid.md) | Diagrams as code (Mermaid), generated from source, freshness-gated | Accepted |
| [0013](0013-dataset-arxiv-llm4se.md) | arXiv AI-for-SE papers as the corpus (incremental OAI-PMH, license-aware ACL) | Accepted |
| [0014](0014-cost-minimization.md) | LLM cost minimization (model tiers, batching, caching, guards) | Accepted |
| [0015](0015-hybrid-llm-backends.md) | Hybrid LLM backends: local (Ollama) for bulk, gateway for answers/judge | Accepted |
| [0016](0016-oss-building-blocks-dagster.md) | OSS building blocks first; Dagster orchestrates ingestion | Accepted |
| [0017](0017-orchestration-module.md) | Separate `orchestration` module for Dagster | Accepted |
| [0018](0018-knowledge-graph-neo4j.md) | Knowledge graph in Neo4j with neo4j-graphrag entity resolution | Accepted |
| [0019](0019-web-frontend-api-boundary.md) | React web front end, `api` module, Python/TypeScript boundary (contract + guardrails) | Accepted |
| [0020](0020-acceptance-tests-playwright.md) | Acceptance tests with Playwright + axe-core (mocked in CI, live locally) | Accepted |
