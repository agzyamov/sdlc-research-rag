# ADR-0005: Qwen3-Embedding (dense) + BM25 (sparse) hybrid retrieval

- Status: Accepted (2026-11-15)
- Modules: `providers` (model factories), `indexing` / `retrieval` (use)

## Context
AI-for-SE questions mix semantics ("how do agents localize faults") with exact tokens (benchmark names such as "SWE-bench Verified" and "HumanEval+", model names, metrics such as pass@1). Dense-only retrieval misses the exact matches.

## Decision
- Dense: `Qwen/Qwen3-Embedding-0.6B` (Apache-2.0) via sentence-transformers on MPS. It belongs to the top open MTEB family and is laptop-sized. Upgrade path: the 4B/8B models, by configuration only.
- Sparse: `Qdrant/bm25` via FastEmbed.
- Fusion: Qdrant Query API with RRF.

## Alternatives
BGE-M3 (dense + sparse in one model, older), harrier-oss-v1 (MTEB multilingual leader but 27B, too large locally), Voyage (hosted, not OSS).

## Consequences
+ Robust on numeric and lexical queries; fully local and free.
− Two embedding passes at ingest time (acceptable at our corpus size).
