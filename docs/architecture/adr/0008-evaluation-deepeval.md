# ADR-0008: DeepEval for RAG evaluation

- Status: Accepted (2026-11-15)
- Module: `evaluation`

## Context
RAG output quality must be measured on a small golden dataset: retrieval precision and recall, faithfulness/groundedness, and answer relevancy.

## Decision
DeepEval (Apache-2.0) with Claude (`claude-haiku-5-5`, configurable) as the judge model:
- **Contextual precision**: are the relevant chunks ranked high?
- **Contextual recall**: does the retrieved context cover the expected answer?
- **Faithfulness**: is every claim in the answer supported by the context? (groundedness / safety)
- **Answer relevancy**: does the answer address the question?
- Plus deterministic metrics: **metadata exact match** against arXiv metadata, **SDLC-phase classification P/R/F1** against a hand-labeled sample, **ACL leakage**, and a **long-context baseline** comparison (the same questions answered from stuffed full texts) for faithfulness, cost and latency.

Golden questions are synthesized with DeepEval's `Synthesizer` from open-licensed papers and reviewed by hand. The judge is a `DeepEvalBaseLLM` wrapper (`evaluation.judge.GatewayJudge`) around the gateway's Claude, using schema-constrained output. DeepEval's GEval adds a reference-based **Correctness** score, used for the long-context comparison. DeepEval telemetry is turned off (`DEEPEVAL_TELEMETRY_OPT_OUT`). The tests run pytest-style (`pytest -m eval`) and act as a regression gate. Reports go to `eval/reports/`, and scores optionally go to Langfuse.

## Alternatives
RAGAS (the reference RAG metric set, but its maintenance signal weakened in 2026; kept as a fallback since the metrics map one-to-one), TruLens, Arize Phoenix evals (ELv2 license).

## Consequences
+ CI-friendly; actively maintained; covers all four target metrics.
− LLM-judge cost and variance. Mitigated by the small golden set, a cheap judge model, and pinned judge prompts.
