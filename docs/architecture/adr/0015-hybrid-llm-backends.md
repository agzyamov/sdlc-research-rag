# ADR-0015: Hybrid LLM backends: local models for bulk work, gateway for quality-critical tasks

- Status: Accepted (2026-11-15), amended the same day: with the corpus limited to 2k papers (ADR-0013), bulk roles default to a cheap gateway model; local stays an optional backend. Refines ADR-0002 and ADR-0014.
- Module: `providers` (`get_llm(role)`); configuration in `core.config`

## Context
LLM calls should cost as little as possible without hurting the quality users see. The developer machine (Apple M4 Pro, 24 GB unified memory) can run a mid-size open model. Claude is reachable through an OpenAI/Azure-compatible LLM gateway, or directly through the Claude API.

## Decision
Every LLM task (role) is configured with a **backend** and a **model**:

| Role | Default backend | Default model | Rationale |
|---|---|---|---|
| `main`: final answers with citations | gateway | Claude Sonnet 5.5 | user-visible quality |
| `judge`: evaluation | gateway | Claude Sonnet 5.5 | must be stronger than and independent of the local models; low volume |
| `extraction`: paper facts (abstract-first) | gateway (local optional) | Claude Haiku 5.5 (`qwen3.5:9b` locally) | bulk (2k papers), short input, structured output |
| `vision`: figure descriptions | gateway (local optional) | Claude Haiku 5.5 (`qwen3.5:9b` locally) | bulk (~3 figures per paper) |
| `fast`: grading, query rewriting | gateway (local optional) | Claude Haiku 5.5 (`qwen3.5:9b` locally) | per question; latency and cost |

- **Local runtime: Ollama** (MLX builds on Apple Silicon), OpenAI-compatible API at `localhost:11434/v1`. One multimodal model serves every local role, so there's one download (~6.6 GB) and no model swapping. Fallback: `gemma4:12b`.
- **Gateway:** Azure-style (`deployment` names) or plain OpenAI-style, selected by `SDLCRAG_GATEWAY_API_STYLE`. URL, key and deployment names exist only in `.env` (gitignored); the repository refers to it generically.
- **Anthropic backend** stays available (API key or `ant auth login --profile`), including the Batch API discount, which only applies there.
- Callers depend only on `BaseChatModel`, so moving a role between backends is configuration only.

## Alternatives
- Everything on the gateway: simplest, but bulk work dominates cost (ADR-0014 estimates).
- Everything local: free, but weaker answers and a judge that grades its own model family.
- LM Studio or raw MLX (`mlx-lm`) instead of Ollama: comparable speed. Ollama is easiest to script and serves an OpenAI-compatible API, including vision.

## Amendment: why bulk roles default to the gateway
At 2k papers, bulk work on a Haiku-class gateway model costs roughly $1–3 in total and finishes in about an hour (parallel requests), against an overnight local run plus ~7 GB of disk and an Ollama setup. Local stays one `.env` line away for $0 or offline runs.

## Consequences
+ Bulk LLM work costs $0. Paid tokens go only to answers and evaluation (a few cents per question).
+ Quality is guarded by QA-7 (extraction F1): if the local model misses the target, `extraction_backend` moves to the gateway by configuration.
− A local model needs about 6–8 GB of RAM while loaded and ~7 GB of disk; throughput is roughly tens of tokens per second, so bulk runs take hours. That's acceptable for ingestion.
− Gateway features differ from the Claude API (no Batch discount; prompt caching depends on the gateway).

## Amendment (2026-11-16): defaults for a fresh clone
Every role now defaults to `anthropic` (an `ANTHROPIC_API_KEY` is all a new user needs). The gateway and local backends are opt-in per role in `.env`.
