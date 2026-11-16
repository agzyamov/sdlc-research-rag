# ADR-0007: OpenFGA for access-control-aware RAG

- Status: Accepted (2026-11-15)
- Module: `access` (only module allowed to talk to OpenFGA); consumer: `retrieval`

## Context
Users must only get answers grounded in documents they may read. Here access derives from each paper's **license**: open-licensed (Creative Commons) papers may be shown to anyone; papers under the arXiv non-exclusive license only to internal users. Group membership and per-paper sharing are modelled as relationships.

## Decision
OpenFGA (Apache-2.0, CNCF) v1.22 with the Postgres datastore. Model in `infra/openfga/model.fga`; store definition (model, base memberships, **authorization tests**) in `infra/openfga/store.fga.yaml`, created by `infra/openfga/bootstrap.sh` with the official `openfga/cli` and tested in CI with `fga model test`.
- **Ingestion** links each paper to its license collection (`paper:<id>#collection@collection:open|restricted`); every planning run reconciles tuples for all indexed papers (idempotent writes).
- **Pre-filter**: `ListObjects(user, can_read, paper)` → Qdrant `paper_id IN [...]` payload filter, so restricted chunks never reach the LLM.
- **Post-filter** (defense in depth): `BatchCheck` on the final chunks.
- **Fail closed:** without a configured store, retrieval raises instead of returning unfiltered results.
- Server setting `OPENFGA_LIST_OBJECTS_MAX_RESULTS=10000` (default 1000 is below the 2k corpus).
- Demo principals (`data/corpus.yaml`): `alice` (public, open papers only), `bob` and `admin` (`group:internal`, all papers).

## Alternatives
Auth0's LangChain `FGARetriever` (`auth0-ai-langchain`) was checked for the post-filter, but even its latest release pins `langchain<0.4` / `langgraph<0.6`, incompatible with LangChain 1.x; the official `openfga-sdk` is used directly.
SpiceDB (stricter Zanzibar consistency, heavier), Cerbos (stateless ABAC, which suits attribute rules but not sharing graphs), a plain metadata role filter (no relationship model; not realistic).

## Consequences
+ A realistic enterprise pattern with an official RAG guide; the policy is decoupled from code.
− An extra service. `ListObjects` cost grows with the number of objects (fine at our scale; the documented mitigation is coarser-grained objects).
