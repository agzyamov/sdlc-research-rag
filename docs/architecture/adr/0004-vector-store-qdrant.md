# ADR-0004: Qdrant as the vector store

- Status: Accepted (2026-11-15)
- Module: `indexing` (only module allowed to talk to Qdrant)

## Context
Requirements: payload filtering (ACL pre-filter on `paper_id`), hybrid dense + sparse search, and add/update/delete of individual documents **without rebuilding** the index.

## Decision
Qdrant (Apache-2.0) v1.20, run in docker (Colima). Embedded local mode (`QdrantClient(path=...)` / `:memory:`) is used in tests. One collection `papers` with named vectors `dense` and `sparse` (BM25), payload indexes on `paper_id`, `published`, `categories`, `license_class`, `section`, `modality`. Point ids are deterministic (UUIDv5 of `paper_id` + chunk hash), so re-ingesting identical content is idempotent.

## Alternatives
Milvus (best at billions of vectors, heavier to operate), Weaviate, pgvector (fine if Postgres already exists), Chroma (prototype-grade), LanceDB (embedded/multimodal, weak on single-row churn).

## Consequences
+ First-class filtering and hybrid search (RRF fusion server-side); cheap upserts and deletes enable incremental updates.
− One more service to run (trivial with compose).
