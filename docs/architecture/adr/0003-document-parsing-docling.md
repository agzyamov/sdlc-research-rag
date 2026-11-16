# ADR-0003: Docling for document parsing

- Status: Accepted (2026-11-15)
- Modules: `ingestion`, `ingestion.multimodal`

## Context
arXiv papers arrive as PDFs (two-column layouts, tables of results, architecture diagrams and charts). Table structure must survive chunking, and pictures must be extractable for multimodal RAG.

## Decision
Docling (MIT, IBM / LF AI & Data) via `langchain-docling`. Its `HybridChunker` keeps chunks structure-aware, tables are exported as Markdown, and picture items are exported for Claude vision.

## Alternatives
MinerU (top OmniDocBench scores, best with a GPU, custom license since 2026-04), Marker (RAIL-M weights), Unstructured, PyMuPDF4LLM (fast, weaker on tables).

## Consequences
+ Runs well on Apple Silicon without a GPU; handles two-column scientific layouts and tables; permissive license.
− Slower than text-only parsers. Mitigated by the incremental ingestion manifest (parse once).
