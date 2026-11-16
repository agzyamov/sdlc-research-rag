"""Ingestion steps as plain functions; orchestration (runs, retries, schedules, partition
status, resume) is Dagster's job, see `assets.py` / `definitions.py` (ADR-0016).

- harvest: arXiv OAI-PMH candidates (initial: walk back in 30-day blocks until the window is
  full; update: everything changed since the last sync)
- plan: keep the newest `max_papers` in-scope papers; decide what to delete and (re)index
- index_paper: download → Docling → LangChain `index()` (skips unchanged chunks, cleans stale)
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml
from langchain_core.documents import Document
from langchain_core.indexing import IndexingResult, RecordManager
from langchain_qdrant import QdrantVectorStore

from sdlcrag.core.models import CorpusFilter, CorpusWindow, LicensePolicy, Paper
from sdlcrag.indexing.store import IndexedPaper, index_paper_chunks
from sdlcrag.ingestion.parsing import parse_pdf
from sdlcrag.ingestion.selection import in_scope, license_class, newest
from sdlcrag.providers.arxiv import PdfDownloader, harvest, today

log = logging.getLogger(__name__)
HARVEST_BLOCK_DAYS = 30
# Bump when parsing/chunking rules change: papers indexed under an older format are re-indexed.
INDEX_FORMAT = 3  # 3: figure descriptions
UPDATE_OVERLAP_DAYS = 1


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_corpus_filter(path: Path) -> CorpusFilter:
    return CorpusFilter.model_validate(_load_yaml(path).get("filter", {}))


def load_corpus_window(path: Path) -> CorpusWindow:
    return CorpusWindow.model_validate(_load_yaml(path).get("window", {}))


def load_license_policy(path: Path) -> LicensePolicy:
    return LicensePolicy.model_validate(_load_yaml(path).get("license_policy", {}))


def set_spec(category: str) -> str:
    """arXiv OAI-PMH set for a category, e.g. cs.SE → cs:cs:SE."""
    archive, _, sub = category.partition(".")
    return f"{archive}:{archive}:{sub}" if sub else archive


def harvest_candidates(
    corpus: CorpusFilter, max_papers: int, since: date | None
) -> tuple[dict[str, Paper], int]:
    """Return (in-scope or withdrawn candidates by id, number of records harvested)."""
    candidates: dict[str, Paper] = {}
    harvested = 0

    def take(spec: str, start: date, end: date | None) -> None:
        nonlocal harvested
        for paper in harvest(spec, start, end):
            harvested += 1
            if paper.withdrawn or in_scope(paper, corpus):
                candidates[paper.paper_id] = paper

    specs = [set_spec(c) for c in corpus.categories]
    if since is not None:  # incremental update
        for spec in specs:
            take(spec, since - timedelta(days=UPDATE_OVERLAP_DAYS), None)
        return candidates, harvested

    # Initial load: a paper published after `start` has a datestamp >= start, so once the
    # newest `max_papers` are all newer than `start`, every one of them has been seen.
    end = today()
    while True:
        start = max(end - timedelta(days=HARVEST_BLOCK_DAYS), corpus.since)
        for spec in specs:
            take(spec, start, end)
        newer = [p for p in candidates.values() if p.published and p.published >= start]
        log.info("harvested back to %s: %d in-scope papers", start, len(newer))
        if len(newer) >= max_papers or start <= corpus.since:
            return candidates, harvested
        end = start - timedelta(days=1)


@dataclass(frozen=True)
class Plan:
    to_delete: list[str]  # withdrawn or evicted from the window
    to_index: list[Paper]  # new, or a newer version than indexed (metadata from the harvest)
    in_scope: int
    window: frozenset[str]  # the papers the corpus should contain
    to_refresh: list[str]  # indexed in an outdated format but unchanged on arXiv


def plan(candidates: dict[str, Paper], indexed: dict[str, IndexedPaper], max_papers: int) -> Plan:
    withdrawn = {pid for pid, p in candidates.items() if p.withdrawn}
    live = {pid: p for pid, p in candidates.items() if not p.withdrawn}

    pool = {pid: ip.published for pid, ip in indexed.items() if pid not in withdrawn}
    pool.update({pid: p.published.isoformat() for pid, p in live.items() if p.published})
    window = newest(pool, max_papers)

    to_delete = sorted((set(indexed) - window) | (withdrawn & set(indexed)))
    to_index = [
        p
        for pid, p in live.items()
        if pid in window and (pid not in indexed or indexed[pid].stale(p.version, INDEX_FORMAT))
    ]
    to_index.sort(key=lambda p: (p.published or date.min, p.paper_id), reverse=True)
    queued = {p.paper_id for p in to_index}
    to_refresh = sorted(
        pid
        for pid, ip in indexed.items()
        if pid in window and pid not in queued and ip.stale(ip.version, INDEX_FORMAT)
    )
    return Plan(to_delete, to_index, len(live), frozenset(window), to_refresh)


def documents(paper: Paper, chunks: list[Document], policy: LicensePolicy) -> list[Document]:
    """Abstract + Docling chunks, all carrying the paper's metadata (incl. license class)."""
    meta = {
        "paper_id": paper.paper_id,
        "version": paper.version,
        "title": paper.title,
        "published": paper.published.isoformat() if paper.published else None,
        "categories": paper.categories,
        "license_class": license_class(paper, policy).value,
        "abs_url": paper.abs_url,
        "index_format": INDEX_FORMAT,
    }
    abstract = Document(
        page_content=f"{paper.title}\n\n{paper.abstract}",
        metadata={**meta, "section": "Abstract", "page": 1, "modality": "abstract"},
    )
    body = [Document(page_content=c.page_content, metadata={**c.metadata, **meta}) for c in chunks]
    return [abstract, *body]


def index_paper(
    paper: Paper,
    *,
    policy: LicensePolicy,
    store: QdrantVectorStore,
    manager: RecordManager,
    downloader: PdfDownloader,
    raw_dir: Path,
) -> IndexingResult:
    pdf = downloader.download(paper, raw_dir)
    try:
        return index_paper_chunks(documents(paper, parse_pdf(pdf), policy), store, manager)
    finally:
        pdf.unlink(missing_ok=True)  # never keep papers on disk (license, space)
