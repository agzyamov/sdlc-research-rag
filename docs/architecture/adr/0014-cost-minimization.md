# ADR-0014: LLM cost minimization

- Status: Accepted (2026-11-15)
- Modules: `core.config` (settings), `providers` (model tiers, LLM output cache, cost accounting), `ingestion` / `extraction` (batching, abstract-first), `evaluation` (cheap judge, baseline on a subset)

## Context
Claude API calls bill the Claude Platform organization's credits. Naive processing of a large corpus (Sonnet for everything, full-text extraction, every figure) would cost several hundred dollars, and every rerun would cost the same again.

## Decision
In order of impact:
1. **Free data first:** arXiv metadata (title, authors, categories, dates, license, abstract) is used as-is. Fact extraction is **abstract-first** and falls back to full-text sections only when the abstract is inconclusive.
2. **Model tiers:** `claude-haiku-5-5` for all bulk work (extraction, figure descriptions, grading, judging), at low effort where reasoning isn't needed. `claude-sonnet-5-5` only for the final answer. All are configurable.
3. **Message Batches API** (−50%) for ingestion-time extraction and figure descriptions.
4. **Never pay twice:** besides the chunk-hash manifest, an on-disk LLM output cache keyed by (model, prompt version, content hash) at `data/cache/llm/`.
5. **Fewer, smaller images:** skip images under 200×200 px, deduplicate by hash, at most 3 figures per paper (preferring captions that mention an architecture, overview or results), downscale to 1024 px max side.
6. **Lean answers:** rerank to the top 6 chunks, `answer_max_tokens=2048`, prompt caching of the static system prompt.
7. **Scale in steps:** about 200 papers for development, 1k for evaluation, then the full corpus.
8. **Cheap evaluation:** Haiku judge, small golden set, `-m eval` only on demand. The long-context baseline runs on a subset (5 questions over a 20-paper slice) with prompt caching.
9. **Guards:** `--dry-run` (token estimate via `count_tokens`), `--max-cost` hard stop, per-run usage/cost log, Langfuse cost per trace. Operators should also set a **monthly workspace spend limit in the Claude Console**.
10. **Development without the API:** unit tests use fake models and recorded responses.

## Consequences
+ Estimated ~$0.30 per 1k papers for extraction + figures, ~$5 for the full corpus, ~$0.01–0.02 per answer, ~$1 per eval run including the baseline.
− Haiku extraction may be less accurate than Sonnet. This is measured by QA-7 (SDLC-phase F1), and the model can be raised per task by configuration if the target is missed.
− Batch results arrive asynchronously (minutes to hours), which is acceptable for ingestion.
