# ADR-0002: Anthropic Claude for generation, vision and evaluation judge

- Status: Accepted (2026-11-15)
- Module: `providers` (factories); consumers: `generation`, `extraction`, `ingestion.multimodal`, `evaluation`

## Decision
- How each task reaches a model (local, gateway or Claude API directly) is decided in [ADR-0015](0015-hybrid-llm-backends.md).
- `claude-sonnet-5-5`: final user-facing answer generation and evaluation judging
- `claude-haiku-5-5`: structured extraction, figure description (vision), relevance grading, query rewriting, evaluation judge (cheap, high volume; see ADR-0014)
- Model ids are configurable via `SDLCRAG_*_MODEL` env vars.
- **Authentication:** browser OAuth via the Anthropic CLI (`ant auth login`) by default. The SDK reads the active profile and refreshes tokens, so no secret sits in `.env`. A static `ANTHROPIC_API_KEY` overrides it (useful for CI). Both bill the Claude Platform (API) organization, not a claude.ai subscription. `providers.llm` injects profile-resolving SDK clients, because langchain-anthropic otherwise pins an empty API key.

## Alternatives
OpenAI GPT, a local LLM via Ollama (free, but weaker at vision and judging).

## Consequences
+ Strong long-context reasoning over research papers, tables and figures; native vision; reliable structured output via tool use.
− Claude has no embedding API, so embeddings come from OSS models (ADR-0005).
− Self-preference bias when Claude both generates and judges. Mitigated by using a different model tier as judge and by deterministic checks (arXiv metadata ground truth, hand-labeled phase sample, QA-7).
