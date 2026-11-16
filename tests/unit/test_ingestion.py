"""Ingestion glue: arXiv record mapping, selection rules, window planning (no network)."""

from datetime import date

from sdlcrag.core.models import Classification, CorpusFilter, LicensePolicy, Paper
from sdlcrag.indexing.store import IndexedPaper
from sdlcrag.ingestion.pipeline import INDEX_FORMAT, plan, set_spec
from sdlcrag.ingestion.selection import in_scope, license_class, newest
from sdlcrag.providers.arxiv import paper_from_metadata

# Shape produced by oaipmh-scythe for an arXivRaw record (one `date` per version).
RAW = {
    "id": ["2611.17316"],
    "date": ["Thu, 12 Nov 2026 18:58:22 GMT", "Fri, 13 Nov 2026 09:00:00 GMT"],
    "size": ["841kb", "850kb"],
    "title": ["CoReMem: Cost-Internalizing\n  Memory for Coding Agents"],
    "authors": ["Peiwen Li (Yale University), Rex Ying"],
    "categories": ["cs.AI cs.CL cs.SE"],
    "license": ["http://creativecommons.org/licenses/by/4.0/"],
    "abstract": ["Coding agents tackle successive tasks with LLMs."],
}
CORPUS = CorpusFilter(categories=["cs.SE"], since=date(2023, 1, 1), keywords=["LLM", "agent"])
POLICY = LicensePolicy(
    open=["http://creativecommons.org/licenses/by/4.0/"],
    restricted=["http://arxiv.org/licenses/nonexclusive-distrib/1.0/"],
)


def paper(pid: str, published: date, version: int = 1, **kw: object) -> Paper:
    return Paper.model_validate(
        {
            "paper_id": pid,
            "title": "LLM agents",
            "categories": ["cs.SE"],
            "published": published,
            "version": version,
            **kw,
        }
    )


def test_paper_from_arxivraw_metadata() -> None:
    p = paper_from_metadata(RAW)
    assert p.paper_id == "2611.17316"
    assert p.version == 2
    assert p.published == date(2026, 11, 12)
    assert p.updated == date(2026, 11, 13)
    assert p.title == "CoReMem: Cost-Internalizing Memory for Coding Agents"
    assert p.categories == ["cs.AI", "cs.CL", "cs.SE"]
    assert not p.withdrawn


def test_withdrawn_detection() -> None:
    assert paper_from_metadata({**RAW, "size": ["841kb", "0kb"]}).withdrawn


def test_scope_filter() -> None:
    assert in_scope(paper_from_metadata(RAW), CORPUS)
    assert not in_scope(paper("1", date(2026, 1, 1), title="Formal proofs", abstract=""), CORPUS)
    assert not in_scope(paper("2", date(2022, 1, 1)), CORPUS)
    assert not in_scope(paper("3", date(2026, 1, 1), categories=["cs.CV"]), CORPUS)


def test_license_class() -> None:
    assert license_class(paper_from_metadata(RAW), POLICY) == Classification.OPEN
    nonexclusive = paper(
        "1", date(2026, 1, 1), license="http://arxiv.org/licenses/nonexclusive-distrib/1.0/"
    )
    assert license_class(nonexclusive, POLICY) == Classification.RESTRICTED
    assert license_class(paper("2", date(2026, 1, 1)), POLICY) == Classification.RESTRICTED


def test_set_spec() -> None:
    assert set_spec("cs.SE") == "cs:cs:SE"


def test_newest_window() -> None:
    pool = {"a": "2026-11-01", "b": "2026-11-03", "c": "2026-11-02"}
    assert newest(pool, 2) == {"b", "c"}


def test_plan_adds_updates_evicts_and_deletes_withdrawn() -> None:
    indexed = {
        "old": IndexedPaper(1, "2026-01-01", INDEX_FORMAT),  # falls out of a 3-paper window
        "rev": IndexedPaper(1, "2026-11-01", INDEX_FORMAT),  # new version available
        "same": IndexedPaper(2, "2026-11-02", INDEX_FORMAT),  # unchanged
        "gone": IndexedPaper(1, "2026-11-03", INDEX_FORMAT),  # withdrawn
    }
    candidates = {
        "rev": paper("rev", date(2026, 11, 1), version=2),
        "same": paper("same", date(2026, 11, 2), version=2),
        "gone": paper("gone", date(2026, 11, 3), withdrawn=True),
        "new": paper("new", date(2026, 11, 4)),
    }
    result = plan(candidates, indexed, max_papers=3)
    assert set(result.to_delete) == {"old", "gone"}
    assert [p.paper_id for p in result.to_index] == ["new", "rev"]
    assert result.window == {"new", "same", "rev"}


def test_dagster_definitions_load() -> None:
    import dagster as dg

    from sdlcrag.orchestration.definitions import defs

    dg.Definitions.validate_loadable(defs)
    keys = {k.to_user_string() for k in defs.resolve_asset_graph().get_all_asset_keys()}
    assert keys == {"corpus_plan", "paper_index", "paper_facts", "entity_resolution"}


def test_reference_chunks_are_flagged() -> None:
    from types import SimpleNamespace as Ns

    from sdlcrag.ingestion.parsing import CompactMetaExtractor

    def chunk(labels: list[str], headings: list[str]) -> Ns:
        items = [Ns(label=Ns(value=label), prov=[Ns(page_no=3)]) for label in labels]
        return Ns(meta=Ns(doc_items=items, headings=headings))

    extract = CompactMetaExtractor().extract_chunk_meta
    assert extract("x", chunk(["reference"], ["Related Work"]))["is_reference"]
    assert extract("x", chunk(["text"], ["7 References"]))["is_reference"]
    assert extract("x", chunk(["list_item"], ["Bibliography"]))["is_reference"]
    meta = extract("x", chunk(["text", "table"], ["4 Evaluation"]))
    assert not meta["is_reference"]
    assert meta["modality"] == "table"


def test_stale_index_format_triggers_reindex() -> None:
    assert IndexedPaper(2, "2026-11-01", index_format=1).stale(2, current_format=2)
    assert not IndexedPaper(2, "2026-11-01", index_format=2).stale(2, current_format=2)
    assert IndexedPaper(1, "2026-11-01", index_format=2).stale(2, current_format=2)


def test_plan_refreshes_outdated_format_without_a_harvest() -> None:
    indexed = {
        "old-format": IndexedPaper(1, "2026-11-01", INDEX_FORMAT - 1),
        "current": IndexedPaper(1, "2026-11-02", INDEX_FORMAT),
    }
    result = plan({}, indexed, max_papers=5)
    assert result.to_index == []
    assert result.to_refresh == ["old-format"]
