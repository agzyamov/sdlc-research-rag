"""Extraction payload and visualization (no LLM, no services)."""

from sdlcrag.core.models import FacetCount, PaperFacts, SdlcPhase, Triple
from sdlcrag.extraction.extractors import facts_by_list
from sdlcrag.visualization.charts import phase_series, top_series
from sdlcrag.visualization.graph import graph_json


def test_facts_by_list_matches_graph_edges() -> None:
    facts = PaperFacts(
        paper_id="2611.1", sdlc_phases=[SdlcPhase.TESTING], models=["GPT-4o"], benchmarks=[]
    )
    lists = facts_by_list(facts)
    assert lists == {
        "sdlc_phases": ["testing"],
        "techniques": [],
        "models": ["GPT-4o"],
        "benchmarks": [],
    }


def test_top_series_sorts_by_count() -> None:
    slices = [
        FacetCount(facet="models", label="GPT-4o", count=1),
        FacetCount(facet="models", label="Claude", count=3),
    ]
    assert top_series(slices) == [{"label": "Claude", "count": 3}, {"label": "GPT-4o", "count": 1}]


def test_graph_merges_shared_entities() -> None:
    triples = [
        Triple(
            subject=p, subject_type="paper", predicate="USES", object="GPT-4o", object_type="model"
        )
        for p in ("Paper A", "Paper B")
    ]
    data = graph_json(triples)
    nodes = {n["id"]: n for n in data["nodes"]}
    assert len(nodes) == 3  # GPT-4o is one node shared by both papers
    assert nodes["GPT-4o"]["degree"] == 2 and nodes["GPT-4o"]["type"] == "model"
    assert nodes["GPT-4o"]["label"] == "GPT-4o"
    assert {(e["source"], e["target"]) for e in data["edges"]} == {
        ("Paper A", "GPT-4o"),
        ("Paper B", "GPT-4o"),
    }


def test_graph_labels_papers_by_title_and_phases_by_lifecycle_name() -> None:
    triples = [
        Triple(
            subject="2611.1",
            subject_type="paper",
            subject_label="A paper title",
            predicate="ADDRESSES",
            object="testing",
            object_type="phase",
        )
    ]
    nodes = {n["id"]: n for n in graph_json(triples)["nodes"]}
    assert nodes["2611.1"]["label"] == "A paper title"
    assert nodes["testing"]["label"] == "4. Testing"
    assert "name" not in nodes["2611.1"]


def test_phase_series_numbers_phases_in_lifecycle_order() -> None:
    slices = [
        FacetCount(facet="sdlc_phases", label="testing", count=11),
        FacetCount(facet="sdlc_phases", label="requirements", count=2),
    ]
    series = phase_series(slices)
    assert [s["label"] for s in series][:4] == [
        "1. Requirements",
        "2. Design",
        "3. Implementation",
        "4. Testing",
    ]
    assert [s["count"] for s in series][:4] == [2, 0, 0, 11]  # zeros kept, lifecycle order
    assert len(series) == 8


def test_only_verbatim_quotes_count_as_evidence() -> None:
    from sdlcrag.extraction.extractors import verified_quote

    abstract = "We evaluate SatisFix on DeepSWE and\nSWE-bench Pro with five LLMs."
    assert verified_quote("evaluate SatisFix on DeepSWE and SWE-bench Pro", abstract) != ""
    assert verified_quote("EVALUATE satisfix", abstract) != ""  # case/whitespace-insensitive
    assert verified_quote("tested on SWE-bench", abstract) == ""  # paraphrase: dropped
    assert verified_quote("", abstract) == ""
