"""Structured fact extraction per paper and the research landscape built from it.

- extraction: Claude (extraction role) with schema-constrained output (`json_schema`) over the
  paper's title and abstract (abstract-first, ADR-0014)
- storage and name normalization: the Neo4j knowledge graph in `indexing.graph`, where
  neo4j-graphrag's resolvers merge near-duplicate names (ADR-0018)
- landscape and graph: Cypher reads over the papers the principal may read (OpenFGA)
"""

import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from sdlcrag.access.policy import get_access_policy
from sdlcrag.core.config import get_settings
from sdlcrag.core.models import (
    FacetCount,
    FactEvidence,
    PaperFacts,
    Principal,
    SdlcPhase,
    Triple,
)
from sdlcrag.indexing.graph import (
    FACT_EDGES,
    PaperRow,
    fact_counts,
    fact_edges,
    matching_paper_ids,
    paper_rows,
)
from sdlcrag.indexing.store import get_client, indexed_papers
from sdlcrag.providers.llm import get_llm

FACTS_FORMAT = 4  # bump when the prompt or schema changes: papers are re-extracted

SYSTEM = """You extract structured facts from software-engineering research papers about AI.
Use only what the title and abstract state explicitly; never guess.
- sdlc_phases: lifecycle phases the paper's contribution targets (1-3, most specific first).
- techniques: specific AI techniques the paper uses or studies, as short canonical terms:
  lower case except acronyms, which stay upper case ("LLM agents", "LLM-as-a-judge");
  spell out other acronyms ("retrieval-augmented generation", not "RAG"). Examples:
  "LLM agents", "retrieval-augmented generation", "fine-tuning", "prompt engineering",
  "multi-agent systems", "reinforcement learning".
  Never list generic terms as techniques, since every paper in this corpus uses them:
  "LLM", "LLMs", "large language models", "language models", "foundation models",
  "generative AI", "AI", "machine learning", "deep learning".
- models: named models, canonical spelling, e.g. "GPT-4o", "Claude 3.5 Sonnet", "Qwen2.5-Coder".
- benchmarks: named datasets or benchmarks, canonical spelling, e.g. "SWE-bench Verified",
  "HumanEval", "Defects4J".
Return at most 5 items per list; return an empty list when nothing is stated.
For every item give `quote`: the shortest verbatim span copied from the title or abstract
(a phrase or sentence, max 200 characters) that states it. Copy it exactly; never paraphrase."""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Title: {title}\n\nAbstract:\n{abstract}")]
)


class _Phase(BaseModel):
    phase: SdlcPhase
    quote: str = Field(description="Verbatim span from the title or abstract")


class _Named(BaseModel):
    name: str
    quote: str = Field(description="Verbatim span from the title or abstract")


class _ExtractedFacts(BaseModel):
    sdlc_phases: list[_Phase] = Field(description="SDLC phases the paper targets")
    techniques: list[_Named] = Field(description="AI techniques used")
    models: list[_Named] = Field(description="Named models used or evaluated")
    benchmarks: list[_Named] = Field(description="Named benchmarks or datasets")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def verified_quote(quote: str, source: str) -> str:
    """The quote if it really occurs in the source (whitespace/case-insensitive), else "".
    Models sometimes paraphrase; a paraphrase must never be shown as evidence."""
    return quote.strip() if quote.strip() and _normalize(quote) in _normalize(source) else ""


def extract_paper_facts(paper_id: str, title: str, abstract: str) -> PaperFacts:
    llm = get_llm("extraction").with_structured_output(_ExtractedFacts, method="json_schema")
    result = _ExtractedFacts.model_validate(
        (PROMPT | llm).invoke({"title": title, "abstract": abstract})
    )
    source = f"{title}\n{abstract}"
    evidence = [
        FactEvidence(kind="sdlc_phases", name=p.phase.value, quote=verified_quote(p.quote, source))
        for p in result.sdlc_phases
    ] + [
        FactEvidence(kind=kind, name=item.name, quote=verified_quote(item.quote, source))
        for kind in ("techniques", "models", "benchmarks")
        for item in getattr(result, kind)
    ]
    return PaperFacts(
        paper_id=paper_id,
        sdlc_phases=[p.phase for p in result.sdlc_phases],
        techniques=[t.name for t in result.techniques],
        models=[m.name for m in result.models],
        benchmarks=[b.name for b in result.benchmarks],
        evidence=evidence,
    )


def facts_by_list(facts: PaperFacts) -> dict[str, list[str]]:
    """Fact lists as plain strings, keyed like `indexing.graph.FACT_EDGES`."""
    data = facts.model_dump(mode="json", exclude={"paper_id", "evidence"})
    return {key: [str(v) for v in data[key]] for key in FACT_EDGES}


def quotes_by_fact(facts: PaperFacts) -> dict[tuple[str, str], str]:
    """(fact list, name) → verified abstract quote, for the graph store."""
    return {(e.kind, e.name): e.quote for e in facts.evidence}


def corpus_size() -> int:
    """All indexed papers, readable or not (only the count is ever shown to a user)."""
    s = get_settings()
    return len(indexed_papers(get_client(), s.qdrant_collection))


def _scope(principal: Principal, filters: dict[str, str] | None) -> list[str]:
    """Readable papers (OpenFGA) narrowed to those having every filtered fact."""
    readable = get_access_policy().readable_paper_ids(principal)
    return matching_paper_ids(readable, filters or {})


def research_landscape(
    principal: Principal, filters: dict[str, str] | None = None
) -> dict[str, list[FacetCount]]:
    """Paper counts per fact value over the papers this principal may read, optionally
    cross-filtered (e.g. {"sdlc_phases": "testing"}: techniques used by testing papers)."""
    readable = _scope(principal, filters)
    return {
        key: [
            FacetCount(facet=key, label=name, count=count)
            for name, count in fact_counts(key, readable, limit=10_000)  # all: the UI decides
        ]
        for key in FACT_EDGES
    }


def papers_with_facts(
    principal: Principal, filters: dict[str, str], paper_id: str | None = None
) -> list[PaperRow]:
    """Drill-through: the readable papers behind a chart slice, bar or graph node (or one
    readable paper when `paper_id` is given)."""
    scope = _scope(principal, filters)
    return paper_rows([p for p in scope if p == paper_id] if paper_id else scope)


def paper_count(principal: Principal, filters: dict[str, str] | None = None) -> int:
    """Number of readable papers in scope (the base for every count on the landscape)."""
    return len(_scope(principal, filters))


NODE_TYPES = {
    "Phase": "phase",
    "Technique": "technique",
    "Model": "model",
    "Benchmark": "benchmark",
}


def knowledge_graph(principal: Principal) -> list[Triple]:
    """Graph edges from the extracted facts of the papers this principal may read."""
    readable = get_access_policy().readable_paper_ids(principal)
    return [
        Triple(
            subject=e.paper_id,
            subject_label=e.paper_title,
            subject_type="paper",
            predicate=e.relation,
            object=e.name,
            object_type=NODE_TYPES.get(e.label, e.label.lower()),
        )
        for e in fact_edges(readable)
    ]
