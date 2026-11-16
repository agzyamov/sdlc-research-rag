# Evaluation

## Metrics (DeepEval with Claude as judge, plus deterministic checks; ADR-0008)

| Metric | Measures | Needs | Target (QA scenario) |
|---|---|---|---|
| **Faithfulness** (groundedness) | share of answer claims supported by the retrieved context (hallucination / safety) | answer, context | ≥ 0.85 (QA-1) |
| **Contextual precision** | relevant chunks ranked above irrelevant ones | question, context, expected answer | ≥ 0.75 (QA-2) |
| **Contextual recall** | how much of the expected answer the retrieved context covers | context, expected answer | ≥ 0.75 (QA-2) |
| **Answer relevancy** | the answer addresses the question | question, answer | ≥ 0.80 (QA-3) |
| **SDLC-phase F1** (deterministic) | extracted SDLC phases vs. a hand-labeled sample of papers | `eval/phase_labels.jsonl` | macro-F1 ≥ 0.80 (QA-7) |
| **Metadata exact match** (deterministic) | answers to metadata questions vs. arXiv metadata | `ground_truth_value` | 1.0 (QA-7) |
| **ACL leakage** (deterministic) | restricted (non-CC) chunks retrieved for a public principal | principal, retrieved paper_ids | = 0 (QA-4) |
| **RAG vs. long-context baseline** | faithfulness, cost and latency of RAG compared with stuffing full texts into Claude's context | the same golden questions | RAG ≥ baseline at ≤ 20% of its cost (QA-9) |

## Golden set: `golden_qa.jsonl`
DeepEval's JSONL golden format. Created with `uv run sdlcrag golden` (DeepEval `Synthesizer`, judge on the gateway), then reviewed by hand:
- one synthetic question per **open-licensed** paper (the file is public, so nothing is derived from papers under the arXiv non-exclusive license); only the question, the reference answer and the source paper id are stored, never chunk text
- five hand-written **cross-paper** questions (`x-001`…`x-005`, asked as the public user `alice`): each needs facts from 2–3 open papers, e.g. "What do the papers say about human oversight of AI coding agents?". Source hit means at least one expected paper is retrieved; the sweep below also reports paper recall
- one hand-written access-control question (`acl-001`: a public user asks about a restricted paper)
- review on 2026-11-16: 10 of 11 synthetic questions kept; `syn-2611.16800` rejected because its reference answer says the source lacks the asked detail

```json
{"input": "the question", "expected_output": "reference answer",
 "additional_metadata": {"id": "syn-2611.16289", "principal": "admin", "category": "synthetic",
                         "expected_paper_ids": ["2611.16289"], "status": "reviewed"}}
```

## Results (20-paper corpus, 2026-11-16)

16 questions: 10 synthetic single-paper, 5 hand-written cross-paper, 1 access-control.

| Metric | All questions | Synthetic (10) | Cross-paper (5) | Target |
|---|---|---|---|---|
| Faithfulness | 0.99 | 0.99 | 1.00 | >= 0.85 |
| Answer relevancy | 0.95 | 0.93 | 0.98 | >= 0.80 |
| Contextual precision | 0.87 | 0.91 | 0.78 | >= 0.75 |
| Contextual recall | 0.79 | 0.97 | **0.43** | >= 0.75 |
| Correctness (GEval vs reference) | 0.71 | 0.90 | **0.32** | >= 0.70 |
| Source hit rate | 1.00 | 1.00 | 1.00 | - |
| ACL leaks | 0 | | | 0 |
| Avg input tokens / cost / latency per question | 4,076 / $0.015 / 11.6 s | | | - |

Judge: Claude Sonnet 5.5 via the gateway. About $1.50 and 5 minutes per run.

**Findings.**
- **Single-paper questions are answered well.** The synthetic questions score high, but optimistically: each was generated from chunks that retrieval then finds, and the same model family writes questions, answers and judges.
- **Cross-paper questions are the real weakness.** Six reranked chunks rarely cover 2–3 papers, so recall and correctness drop. Faithfulness stays at 1.00: the system answers partially from what it retrieved and does not fill gaps from general knowledge, which is the intended "honest absence" behavior.
- **A fix is available off the shelf but not applied, because of cost.** Query decomposition (LangChain `MultiQueryRetriever`: one retrieval per sub-question) would raise recall at the price of extra LLM calls per question.
- **The long-context baseline (QA-9) was not run.** Each baseline call puts all open papers into one prompt (about 220k tokens). That is close to the gateway's per-minute token limit (240k), and 15 questions would use about half of the daily token limit. The code exists (`sdlcrag eval --baseline`); running it on two or three questions is possible on a fresh daily budget.
- **The corpus stays at 20 papers** (token budget), so these numbers describe a small haystack.

## Retrieval tuning (no LLM cost)
`uv run sdlcrag tune-retrieval` sweeps candidates, top-k and reranking with the production retriever and scores each setting against the expected papers: MRR, paper recall@k, and paper precision@k (share of top-k chunks from expected papers, a cheap proxy for contextual precision).

On the 20-paper corpus (15 questions, 2026-11-16), the defaults (40 candidates, top 6, rerank on) were already the best setting: MRR 1.00, recall 0.92, precision 0.94. Without reranking, precision drops to 0.82. Re-run it after changing retrieval settings.

## Run
```bash
uv run sdlcrag golden               # (re)synthesize goldens; review before use
uv run sdlcrag tune-retrieval       # retrieval sweep (local, free)
uv run sdlcrag eval                 # report -> eval/reports/<timestamp>.json (+ latest.json); also shown in the app
uv run sdlcrag eval --baseline      # adds the long-context baseline (~$0.45 per question at 20 papers)
uv run pytest -m eval               # regression gate: fails below targets or on any ACL leak
```
