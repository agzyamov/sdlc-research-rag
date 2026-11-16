"""Report aggregation (no LLM calls)."""

from sdlcrag.evaluation.runner import EvalReport, ItemResult, summarize, summary_markdown


def item(i: str, **kw: object) -> ItemResult:
    r = ItemResult(i, "q", "admin", "a", [])
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def test_summary_aggregates_scores_hits_leaks_and_cost() -> None:
    items = [
        item("a", scores={"Faithfulness": 1.0}, source_hit=True, cost_usd=0.02, latency_s=4),
        item("b", scores={"Faithfulness": 0.8}, source_hit=False, cost_usd=0.04, latency_s=6),
        item("acl", acl_leak=False),
    ]
    s = summarize(items)
    assert s["Faithfulness"] == 0.9
    assert s["Source hit rate"] == 0.5
    assert s["ACL leaks"] == 0.0
    assert s["Avg cost per question (USD)"] == 0.02


def test_markdown_shows_baseline_column_when_present() -> None:
    report = EvalReport(
        "t", "judge", {"Correctness": 0.9}, [], baseline_summary={"Correctness": 0.8}
    )
    md = summary_markdown(report)
    assert "Long-context baseline" in md
    assert "| Correctness | 0.9 | 0.8 | >= 0.7 |" in md
