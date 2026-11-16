# ADR-0009: Langfuse for tracing, datasets and scores

- Status: Accepted (2026-11-15)
- Modules: `providers` (callback handler factory), `evaluation` (score export)

## Decision
Self-hosted Langfuse v4 (MIT core) under the compose profile `observability`, wired through the LangChain callback handler. It is optional: when no keys are set, tracing is a no-op.

## Alternatives
Arize Phoenix (OTel-native, but Elastic License 2.0 is not OSI open source), LangSmith (proprietary SaaS).

## Consequences
+ Trace-level debugging of the graph, cost and latency tracking (QA-8), eval scores stored next to traces.
− A heavy local stack (Postgres, ClickHouse, Redis, MinIO). That is why it is opt-in.
