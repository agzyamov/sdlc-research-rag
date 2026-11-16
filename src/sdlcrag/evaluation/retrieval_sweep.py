"""Retrieval parameter sweep: deterministic, local, no LLM calls.

For each golden with expected papers, run the production retriever (`retrieval.build_retriever`)
with different candidate counts, top-k and reranking on/off, and measure against the expected
paper ids:
- MRR: reciprocal rank of the first chunk from an expected paper
- paper recall@k: share of expected papers present in the top-k
- paper precision@k: share of top-k chunks that come from an expected paper (a cheap proxy for
  DeepEval's contextual precision)
Used to pick `retrieval_candidates` / `retrieval_top_k` before paying for a judged run.
"""

from dataclasses import dataclass
from itertools import product
from statistics import mean

from deepeval.dataset import Golden
from langchain_core.documents import Document

from sdlcrag.access.policy import get_access_policy
from sdlcrag.core.models import Principal
from sdlcrag.indexing.store import open_index
from sdlcrag.retrieval.retriever import acl_filter, build_retriever


@dataclass
class SweepRow:
    candidates: int
    top_k: int
    rerank: bool
    mrr: float
    recall: float
    precision: float


def _scores(docs: list[Document], expected: set[str]) -> tuple[float, float, float]:
    ids = [str(d.metadata.get("paper_id")) for d in docs]
    first = next((i for i, pid in enumerate(ids, 1) if pid in expected), None)
    mrr = 1 / first if first else 0.0
    recall = len(expected & set(ids)) / len(expected)
    precision = sum(pid in expected for pid in ids) / len(ids) if ids else 0.0
    return mrr, recall, precision


def sweep(
    goldens: list[Golden],
    candidates: tuple[int, ...] = (20, 40, 80),
    top_ks: tuple[int, ...] = (4, 6, 8),
) -> list[SweepRow]:
    store = open_index().store
    access = get_access_policy()
    cases = []
    for g in goldens:
        meta = g.additional_metadata or {}
        expected = set(meta.get("expected_paper_ids", []))
        if expected:
            principal = Principal(user_id=meta.get("principal", "admin"))
            cases.append((g.input, expected, acl_filter(access.readable_paper_ids(principal))))
    rows: list[SweepRow] = []
    for n, k, rerank in product(candidates, top_ks, (True, False)):
        if not rerank and n != candidates[0]:
            continue  # without reranking the candidate count does not matter
        results = []
        for query, expected, flt in cases:
            if rerank:
                retriever = build_retriever(store, candidates=n, top_k=k, qdrant_filter=flt)
            else:
                retriever = store.as_retriever(search_kwargs={"k": k, "filter": flt})
            results.append(_scores(retriever.invoke(query), expected))
        mrr, recall, precision = (round(mean(col), 3) for col in zip(*results, strict=True))
        rows.append(SweepRow(n if rerank else 0, k, rerank, mrr, recall, precision))
    return rows
