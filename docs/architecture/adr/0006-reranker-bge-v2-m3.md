# ADR-0006: bge-reranker-v2-m3 cross-encoder reranking

- Status: Accepted (2026-11-15)
- Modules: `providers` (factory), `retrieval` (use)

## Decision
Retrieve the top 30–50 candidates by hybrid search, rerank them with `BAAI/bge-reranker-v2-m3` (Apache-2.0, sentence-transformers `CrossEncoder`), and keep the top k (5–8) for generation.

## Alternatives
Qwen3-Reranker (stronger on benchmarks, heavier and less mature tooling), Cohere Rerank (hosted, not OSS), LLM-as-reranker (slow and costly).

## Consequences
+ Measurable lift in contextual precision (QA-2) at low latency on MPS.
− Adds ~100–300 ms per query locally.
