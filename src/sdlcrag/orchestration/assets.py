"""Dagster assets for the corpus (ADR-0016).

- `corpus_plan`: harvest arXiv, apply the rolling window, delete withdrawn/evicted papers,
  register one dynamic partition per paper to (re)index. Its materialization metadata records
  `harvested_until`, which is the next incremental sync's starting point.
- `paper_index`: one partition per paper (arXiv id): download → parse → incremental index.
  Dagster provides per-paper status, retries, resume (only missing/failed partitions run),
  lineage and the UI; `AutomationCondition.eager()` indexes newly registered papers.
  Only network errors are retried (`RetryRequested`); deterministic failures fail fast.
"""

from datetime import date

import dagster as dg
import httpx

from sdlcrag.access.policy import get_access_policy
from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Classification, Paper
from sdlcrag.extraction.extractors import (
    FACTS_FORMAT,
    extract_paper_facts,
    facts_by_list,
    quotes_by_fact,
)
from sdlcrag.indexing.graph import (
    delete_paper_graph,
    facts_format,
    resolve_entities,
    write_paper_facts,
)
from sdlcrag.indexing.store import delete_paper, indexed_papers, open_index, paper_abstracts
from sdlcrag.ingestion.pipeline import (
    INDEX_FORMAT,
    harvest_candidates,
    index_paper,
    load_corpus_filter,
    load_license_policy,
    plan,
)
from sdlcrag.ingestion.selection import license_class
from sdlcrag.providers.arxiv import PdfDownloader, fetch_paper, today

PAPERS_PARTITION = "papers"
PAPERS = dg.DynamicPartitionsDefinition(name=PAPERS_PARTITION)


class SyncConfig(dg.Config):
    max_papers: int = 20
    incremental: bool = True


def _last_harvest(instance: dg.DagsterInstance) -> date | None:
    event = instance.get_latest_materialization_event(dg.AssetKey("corpus_plan"))
    mat = event.asset_materialization if event else None
    value = mat.metadata.get("harvested_until") if mat else None
    return date.fromisoformat(str(value.value)) if value is not None else None


@dg.asset(group_name="corpus", kinds={"arxiv", "qdrant"})
def corpus_plan(context: dg.AssetExecutionContext, config: SyncConfig) -> dict[str, dict]:
    """Papers to (re)index, keyed by arXiv id."""
    s = get_settings()
    since = _last_harvest(context.instance) if config.incremental else None
    candidates, harvested = harvest_candidates(
        load_corpus_filter(s.corpus_path), config.max_papers, since
    )
    idx = open_index()
    store, manager, client = idx.store, idx.manager, idx.client
    p = plan(candidates, indexed_papers(client, s.qdrant_collection), config.max_papers)

    access = get_access_policy()
    deleted_chunks = 0
    for pid in p.to_delete:
        deleted_chunks += delete_paper(pid, store, manager)
        delete_paper_graph(pid)
        access.unregister_paper(pid)
    # Reconcile ACL tuples for everything indexed (idempotent; repairs any missed write).
    access.register_papers(
        {
            pid: Classification(ip.license_class)
            for pid, ip in indexed_papers(client, s.qdrant_collection).items()
        }
    )
    # Unregister every paper outside the window, indexed or not, so leftovers from an
    # earlier (larger) plan are never processed.
    for pid in set(context.instance.get_dynamic_partitions(PAPERS_PARTITION)) - p.window:
        context.instance.delete_dynamic_partition(PAPERS_PARTITION, pid)
    context.instance.add_dynamic_partitions(
        PAPERS_PARTITION, [x.paper_id for x in p.to_index] + p.to_refresh
    )

    context.add_output_metadata(
        {
            "harvested_until": today().isoformat(),
            "records_harvested": harvested,
            "papers_in_scope": p.in_scope,
            "papers_to_index": len(p.to_index),
            "papers_to_refresh": len(p.to_refresh),
            "papers_deleted": len(p.to_delete),
            "chunks_deleted": deleted_chunks,
        }
    )
    planned = {x.paper_id: x.model_dump(mode="json") for x in p.to_index}
    # Outdated-format papers carry no harvested metadata; paper_index re-fetches it.
    return planned | {pid: {} for pid in p.to_refresh}


@dg.asset(
    group_name="corpus",
    kinds={"docling", "qdrant"},
    partitions_def=PAPERS,
    automation_condition=dg.AutomationCondition.eager(),
)
def paper_index(
    context: dg.AssetExecutionContext, corpus_plan: dict[str, dict]
) -> dg.MaterializeResult:
    """Chunks of one paper in the hybrid index."""
    s = get_settings()
    pid = context.partition_key
    paper = Paper.model_validate(corpus_plan[pid]) if corpus_plan.get(pid) else fetch_paper(pid)
    idx = open_index()
    store, manager, client = idx.store, idx.manager, idx.client
    indexed = indexed_papers(client, s.qdrant_collection).get(pid)
    if indexed is not None and not indexed.stale(paper.version, INDEX_FORMAT):
        return dg.MaterializeResult(
            metadata={"skipped": "already indexed", "version": paper.version}
        )

    policy = load_license_policy(s.corpus_path)
    downloader = PdfDownloader()
    try:
        result = index_paper(
            paper,
            policy=policy,
            store=store,
            manager=manager,
            downloader=downloader,
            raw_dir=s.raw_dir,
        )
    except (httpx.TransportError, httpx.HTTPStatusError) as exc:
        # Only network problems are worth retrying; parse or config errors fail fast.
        raise dg.RetryRequested(max_retries=2, seconds_to_wait=30) from exc
    finally:
        downloader.close()
    get_access_policy().register_papers({pid: license_class(paper, policy)})
    return dg.MaterializeResult(
        metadata={
            "title": paper.title,
            "version": paper.version,
            "url": dg.MetadataValue.url(paper.abs_url),
            "chunks_added": result["num_added"],
            "chunks_updated": result["num_updated"],
            "chunks_skipped": result["num_skipped"],
            "chunks_deleted": result["num_deleted"],
        }
    )


@dg.asset(
    group_name="corpus",
    kinds={"anthropic", "neo4j"},
    partitions_def=PAPERS,
    deps=[paper_index],
    automation_condition=dg.AutomationCondition.eager(),
)
def paper_facts(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    """SDLC phases, techniques, models and benchmarks of one paper (Neo4j knowledge graph)."""
    s = get_settings()
    pid = context.partition_key
    client = open_index().client
    rows = paper_abstracts(client, s.qdrant_collection, [pid])
    if not rows:
        return dg.MaterializeResult(metadata={"skipped": "paper not indexed"})
    row = rows[0]
    if facts_format(pid) == FACTS_FORMAT:
        return dg.MaterializeResult(metadata={"skipped": "facts up to date"})
    facts = extract_paper_facts(pid, row.title, row.text)
    write_paper_facts(
        pid,
        row.title,
        row.license_class,
        facts_by_list(facts),
        FACTS_FORMAT,
        quotes=quotes_by_fact(facts),
        published=row.published,
    )
    return dg.MaterializeResult(
        metadata={
            "title": row.title,
            "sdlc_phases": ", ".join(p.value for p in facts.sdlc_phases),
            "techniques": ", ".join(facts.techniques),
            "models": ", ".join(facts.models),
            "benchmarks": ", ".join(facts.benchmarks),
        }
    )


@dg.asset(
    group_name="corpus",
    kinds={"neo4j"},
    deps=[paper_facts],
    automation_condition=dg.AutomationCondition.eager(),
)
def entity_resolution() -> dg.MaterializeResult:
    """Merge spelling variants of technique names across papers (neo4j-graphrag resolver)."""
    return dg.MaterializeResult(metadata={"merged_groups": resolve_entities()})
