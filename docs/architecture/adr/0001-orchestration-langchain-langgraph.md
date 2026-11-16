# ADR-0001: LangChain + LangGraph for orchestration

- Status: Accepted (2026-11-15)
- Modules: `generation`, `extraction` (graph and chains); integrations used in `providers`, `indexing`, `ingestion`

## Context
We need a GenAI framework for RAG with corrective loops (grade → rewrite → retry), structured output for extraction, and integrations for Claude, Qdrant and Docling.

## Decision
LangChain 1.x for the integrations (`langchain-anthropic`, `langchain-qdrant`, `langchain-docling`) and LangGraph 1.x for the RAG state machine.

## Alternatives
LlamaIndex (strong ingestion and indexing, less explicit control flow), Haystack (pipeline-oriented, smaller ecosystem), plain SDK (most code to write).

## Consequences
+ Explicit, testable graph nodes; the largest integration ecosystem; native callbacks for Langfuse.
− Abstraction churn between versions. Mitigated by keeping LangChain types inside the adapter modules where possible.
