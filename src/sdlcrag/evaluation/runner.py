"""Evaluation runner: DeepEval RAG metrics with the gateway judge, plus deterministic checks.

Per golden: run the real pipeline (`generation.answer`) as the golden's principal, then score
- DeepEval: faithfulness, answer relevancy, contextual precision, contextual recall
- correctness: DeepEval GEval against the reference answer
- source hit: the paper the question was generated from is among the retrieved sources
- ACL leak (acl goldens): no restricted source reaches the principal
- tokens, cost and latency (LangChain usage callback)
The long-context baseline (QA-9) answers the same questions with all open papers in the prompt
and is scored on correctness and relevancy, which do not depend on retrieved chunks.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean

from deepeval.dataset import Golden
from deepeval.evaluate.configs import AsyncConfig, DisplayConfig
from deepeval.evaluate.evaluate import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    BaseMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langchain_core.callbacks import UsageMetadataCallbackHandler, get_usage_metadata_callback
from qdrant_client import models

from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Answer, Principal
from sdlcrag.evaluation.judge import GatewayJudge
from sdlcrag.generation.graph import answer
from sdlcrag.indexing.store import get_client
from sdlcrag.providers.llm import get_llm

# QA scenario targets (docs/architecture/04-quality-attributes.md)
THRESHOLDS = {
    "Faithfulness": 0.85,
    "Answer Relevancy": 0.80,
    "Contextual Precision": 0.75,
    "Contextual Recall": 0.75,
    "Correctness": 0.70,
}
# Approximate list prices (USD per 1M tokens: input, output), for cost reporting only.
PRICES = {"sonnet": (2.0, 10.0), "haiku": (0.10, 0.50)}

BASELINE_SYSTEM = (
    "You answer questions about research on AI in software engineering using ONLY the papers "
    "below. Name the paper (arXiv id) you rely on. If the papers do not contain the answer, "
    "say so plainly instead of guessing.\n\n{corpus}"
)


@dataclass
class ItemResult:
    id: str
    question: str
    principal: str
    answer: str
    sources: list[dict]
    scores: dict[str, float] = field(default_factory=dict)
    source_hit: bool | None = None
    acl_leak: bool | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0


@dataclass
class EvalReport:
    created: str
    judge: str
    summary: dict[str, float]
    items: list[ItemResult]
    baseline_summary: dict[str, float] = field(default_factory=dict)
    baseline_items: list[ItemResult] = field(default_factory=list)


def _meta(g: Golden) -> dict:
    return g.additional_metadata or {}


def _usage(cb: UsageMetadataCallbackHandler) -> tuple[int, int, float]:
    """Sum token usage over all models used in a call and price it."""
    tokens_in = tokens_out = 0
    cost = 0.0
    for model, usage in cb.usage_metadata.items():
        tin, tout = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        price_in, price_out = PRICES["haiku" if "haiku" in model else "sonnet"]
        tokens_in, tokens_out = tokens_in + tin, tokens_out + tout
        cost += (tin * price_in + tout * price_out) / 1e6
    return tokens_in, tokens_out, round(cost, 5)


def _correctness(judge: GatewayJudge) -> GEval:
    return GEval(
        name="Correctness",
        criteria=(
            "Is the actual output factually consistent with the expected output? Penalize "
            "contradictions and missing key facts or numbers; extra correct detail is fine."
        ),
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        model=judge,
        threshold=THRESHOLDS["Correctness"],
    )


def _score(cases: list[LLMTestCase], metrics: list[BaseMetric], items: list[ItemResult]) -> None:
    outcome = evaluate(
        cases,
        metrics,
        async_config=AsyncConfig(max_concurrent=4),
        display_config=DisplayConfig(print_results=False, show_indicator=False),
    )
    by_id = {r.id: r for r in items}
    for tr in outcome.test_results:
        for md in tr.metrics_data or []:
            by_id[tr.name].scores[md.name.removesuffix(" [GEval]")] = float(md.score or 0.0)


def run_evaluation(goldens: list[Golden]) -> EvalReport:
    judge = GatewayJudge("judge")
    results: list[ItemResult] = []
    cases: list[LLMTestCase] = []
    for g in goldens:
        meta = _meta(g)
        principal = meta.get("principal", "admin")
        start = time.perf_counter()
        with get_usage_metadata_callback() as cb:
            ans: Answer = answer(g.input, Principal(user_id=principal))
        item = ItemResult(
            meta["id"],
            g.input,
            principal,
            ans.text,
            [s.model_dump(exclude={"text"}) for s in ans.sources],
        )
        item.input_tokens, item.output_tokens, item.cost_usd = _usage(cb)
        item.latency_s = round(time.perf_counter() - start, 2)
        retrieved = {s.paper_id for s in ans.sources}
        if meta.get("category") == "acl":
            restricted = set(meta.get("restricted_paper_ids", []))
            item.acl_leak = bool(retrieved & restricted) or any(
                s.license_class == "restricted" for s in ans.sources
            )
        else:
            item.source_hit = bool(retrieved & set(meta.get("expected_paper_ids", [])))
            cases.append(
                LLMTestCase(
                    input=g.input,
                    actual_output=ans.text,
                    expected_output=g.expected_output,
                    retrieval_context=[s.text for s in ans.sources] or [""],
                    name=meta["id"],
                )
            )
        results.append(item)

    metrics: list[BaseMetric] = [
        FaithfulnessMetric(threshold=THRESHOLDS["Faithfulness"], model=judge),
        AnswerRelevancyMetric(threshold=THRESHOLDS["Answer Relevancy"], model=judge),
        ContextualPrecisionMetric(threshold=THRESHOLDS["Contextual Precision"], model=judge),
        ContextualRecallMetric(threshold=THRESHOLDS["Contextual Recall"], model=judge),
        _correctness(judge),
    ]
    _score(cases, metrics, results)
    return EvalReport(
        created=datetime.now().isoformat(timespec="seconds"),
        judge=f"{judge.chat.__class__.__name__}:{getattr(judge.chat, 'deployment_name', '')}",
        summary=summarize(results),
        items=results,
    )


def open_corpus_text() -> str:
    """Full text of all open-licensed papers, grouped by paper (the long-context baseline)."""
    s = get_settings()
    client = get_client()
    by_paper: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            s.qdrant_collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.license_class", match=models.MatchValue(value="open")
                    )
                ]
            ),
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            payload = p.payload or {}
            meta = payload.get("metadata", {})
            pid = str(meta.get("paper_id"))
            titles[pid] = str(meta.get("title", ""))
            by_paper.setdefault(pid, []).append(str(payload.get("page_content", "")))
        if offset is None:
            break
    return "\n\n".join(
        f"=== Paper arXiv:{pid}: {titles[pid]} ===\n" + "\n\n".join(chunks)
        for pid, chunks in by_paper.items()
    )


def run_baseline(goldens: list[Golden], report: EvalReport) -> EvalReport:
    """Long-context baseline: same questions, all open papers stuffed into the prompt."""
    judge = GatewayJudge("judge")
    llm = get_llm("main")
    system = BASELINE_SYSTEM.format(corpus=open_corpus_text())
    items: list[ItemResult] = []
    cases: list[LLMTestCase] = []
    for g in goldens:
        meta = _meta(g)
        if meta.get("category") == "acl":
            continue  # the baseline has no access control by construction
        start = time.perf_counter()
        with get_usage_metadata_callback() as cb:
            text = str(llm.invoke([("system", system), ("human", g.input)]).content)
        item = ItemResult(meta["id"], g.input, "admin", text, [])
        item.input_tokens, item.output_tokens, item.cost_usd = _usage(cb)
        item.latency_s = round(time.perf_counter() - start, 2)
        items.append(item)
        cases.append(
            LLMTestCase(
                input=g.input,
                actual_output=text,
                expected_output=g.expected_output,
                name=meta["id"],
            )
        )
    metrics: list[BaseMetric] = [
        AnswerRelevancyMetric(threshold=THRESHOLDS["Answer Relevancy"], model=judge),
        _correctness(judge),
    ]
    _score(cases, metrics, items)
    report.baseline_items = items
    report.baseline_summary = summarize(items)
    return report


def summarize(results: list[ItemResult]) -> dict[str, float]:
    summary: dict[str, float] = {}
    for name in THRESHOLDS:
        values = [r.scores[name] for r in results if name in r.scores]
        if values:
            summary[name] = round(mean(values), 3)
    hits = [r.source_hit for r in results if r.source_hit is not None]
    if hits:
        summary["Source hit rate"] = round(sum(hits) / len(hits), 3)
    leaks = [r.acl_leak for r in results if r.acl_leak is not None]
    if leaks:
        summary["ACL leaks"] = float(sum(leaks))
    if results:
        summary["Avg input tokens"] = round(mean(r.input_tokens for r in results))
        summary["Avg cost per question (USD)"] = round(mean(r.cost_usd for r in results), 4)
        summary["Avg latency (s)"] = round(mean(r.latency_s for r in results), 1)
    return summary


def load_latest_report(reports_dir: Path) -> EvalReport | None:
    """The latest evaluation report as written by `write_report`, if any."""
    path = reports_dir / "latest.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    items = [ItemResult(**i) for i in data.pop("items", [])]
    baseline = [ItemResult(**i) for i in data.pop("baseline_items", [])]
    return EvalReport(**data, items=items, baseline_items=baseline)


def write_report(report: EvalReport, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    data = json.dumps(asdict(report), indent=2, ensure_ascii=False)
    path = reports_dir / f"{report.created.replace(':', '-')}.json"
    path.write_text(data)
    (reports_dir / "latest.json").write_text(data)
    return path


def summary_markdown(report: EvalReport) -> str:
    base = report.baseline_summary
    header = (
        ["| Metric | RAG | Long-context baseline | Target |", "|---|---|---|---|"]
        if base
        else ["| Metric | Score | Target |", "|---|---|---|"]
    )
    lines = [f"Run {report.created}, judge `{report.judge}`, {len(report.items)} questions.", ""]
    lines += header
    for name, value in report.summary.items():
        target = THRESHOLDS.get(name)
        target_text = "0" if name == "ACL leaks" else ("-" if target is None else f">= {target}")
        if base:
            lines.append(f"| {name} | {value} | {base.get(name, '-')} | {target_text} |")
        else:
            lines.append(f"| {name} | {value} | {target_text} |")
    return "\n".join(lines) + "\n"
