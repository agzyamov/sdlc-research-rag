"""Knowledge graph store against a live Neo4j (`pytest -m integration`).

Requires: `docker compose up -d neo4j`. Uses throwaway paper ids and removes them afterwards.
"""

import pytest

pytestmark = pytest.mark.integration

A, B = "test-graph-a", "test-graph-b"


@pytest.fixture
def graph():
    from sdlcrag.indexing import graph

    try:
        graph.get_driver().verify_connectivity()
    except Exception:
        pytest.skip("Neo4j not reachable")
    yield graph
    for pid in (A, B):
        graph.delete_paper_graph(pid)


def test_spelling_variants_merge_and_reads_respect_paper_filter(graph) -> None:
    graph.write_paper_facts(
        A, "Paper A", "open", {"techniques": ["zzqx tool agents"], "models": ["Zz-Model 5"]}, 2
    )
    graph.write_paper_facts(
        B,
        "Paper B",
        "restricted",
        {"techniques": ["zzqx tool agent"], "models": ["Zz-Model 5.5"]},
        2,
    )
    graph.resolve_entities()

    techniques = dict(graph.fact_counts("techniques", [A, B], limit=1000))
    zz = {name: n for name, n in techniques.items() if name.startswith("zzqx")}
    assert list(zz.values()) == [2]  # one merged node used by both papers

    models = dict(graph.fact_counts("models", [A, B], limit=1000))
    assert models.get("Zz-Model 5") == 1 and models.get("Zz-Model 5.5") == 1  # never fuzzy-merged

    only_a = {e.paper_title for e in graph.fact_edges([A])}
    assert only_a == {"Paper A"}  # the paper filter (readable ids) is applied
    assert graph.facts_format(A) == 2


def test_rewrite_replaces_edges_and_delete_removes_orphans(graph) -> None:
    graph.write_paper_facts(A, "Paper A", "open", {"benchmarks": ["ZzBench-old"]}, 1)
    graph.write_paper_facts(A, "Paper A", "open", {"benchmarks": ["ZzBench-new"]}, 2)
    assert [n for n, _ in graph.fact_counts("benchmarks", [A])] == ["ZzBench-new"]

    graph.delete_paper_graph(A)
    assert graph.fact_counts("benchmarks", [A]) == []
    assert graph.facts_format(A) is None
