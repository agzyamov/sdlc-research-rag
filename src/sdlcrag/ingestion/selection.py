"""Corpus selection rules from data/corpus.yaml: scope filter, license class, rolling window."""

import re
from functools import lru_cache

from sdlcrag.core.models import Classification, CorpusFilter, LicensePolicy, Paper


@lru_cache(maxsize=8)
def _keyword_pattern(keywords: tuple[str, ...]) -> re.Pattern[str]:
    # Word-start match, so "LLM" also matches "LLMs" and "agent" matches "agentic".
    return re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + ")", re.IGNORECASE)


def in_scope(paper: Paper, corpus: CorpusFilter) -> bool:
    if not set(paper.categories) & set(corpus.categories):
        return False
    if paper.published is None or paper.published < corpus.since:
        return False
    if not corpus.keywords:
        return True
    return bool(_keyword_pattern(tuple(corpus.keywords)).search(f"{paper.title} {paper.abstract}"))


def license_class(paper: Paper, policy: LicensePolicy) -> Classification:
    lic = (paper.license or "").rstrip("/") + "/"
    if lic in {u.rstrip("/") + "/" for u in policy.open}:
        return Classification.OPEN
    if lic in {u.rstrip("/") + "/" for u in policy.restricted}:
        return Classification.RESTRICTED
    return Classification(policy.default)


def newest(papers: dict[str, str], max_papers: int) -> set[str]:
    """Pick the ids of the newest `max_papers` from {paper_id: published ISO date}."""
    ranked = sorted(papers.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    return {pid for pid, _ in ranked[:max_papers]}
