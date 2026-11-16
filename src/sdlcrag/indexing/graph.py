"""Knowledge graph store: Neo4j with neo4j-graphrag entity resolution (ADR-0018).

Graph: `(:Paper {paper_id, title, license_class, facts_format})` with edges
`ADDRESSES → :Phase`, `USES → :Technique | :Model`, `EVALUATED_ON → :Benchmark`.
Fact nodes carry neo4j-graphrag's `__Entity__` label and are written with `MERGE` on `name`,
so exact duplicates never arise. Spelling variants of technique names ("LLM agent" /
"LLM Agents" / "LLM-agents") are merged by neo4j-graphrag's `FuzzyMatchResolver` (RapidFuzz).
Synonyms and acronyms are handled at extraction (the prompt spells acronyms out); the spaCy
semantic resolver was tried and rejected: general-purpose word vectors score
"RAG" vs "retrieval-augmented generation" at 0.26. Models and benchmarks are proper names
("Claude Opus 5" ≠ "Claude Opus 5.5"), so they are matched exactly only.

Every read takes the principal's readable paper ids (OpenFGA), so charts and the graph never
show facts of papers the user may not read.
"""

import asyncio
from dataclasses import dataclass
from functools import cache
from typing import LiteralString, cast

from neo4j import Driver, GraphDatabase
from neo4j_graphrag.components.resolver import FuzzyMatchResolver

from sdlcrag.core.config import get_settings

# fact list → (relationship type, node label)
FACT_EDGES = {
    "sdlc_phases": ("ADDRESSES", "Phase"),
    "techniques": ("USES", "Technique"),
    "models": ("USES", "Model"),
    "benchmarks": ("EVALUATED_ON", "Benchmark"),
}
RESOLVED_LABELS = "WHERE entity:Technique"


def _cypher(text: str) -> LiteralString:
    """Query text with labels/types from FACT_EDGES (constants, never user input); Cypher
    cannot take labels as parameters."""
    return cast(LiteralString, text)


@cache
def get_driver() -> Driver:
    s = get_settings()
    return GraphDatabase.driver(
        s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password.get_secret_value())
    )


def ensure_schema(driver: Driver) -> None:
    db = get_settings().neo4j_database
    driver.execute_query(
        "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
        database_=db,
    )
    for _, label in FACT_EDGES.values():
        driver.execute_query(
            _cypher(f"CREATE INDEX {label.lower()}_name IF NOT EXISTS FOR (n:{label}) ON (n.name)"),
            database_=db,
        )


def write_paper_facts(
    paper_id: str,
    title: str,
    license_class: str,
    facts: dict[str, list[str]],
    facts_format: int,
    *,
    quotes: dict[tuple[str, str], str] | None = None,
    published: str | None = None,
) -> None:
    """Replace one paper's fact edges (idempotent; re-extraction overwrites). Each edge keeps
    the abstract quote supporting it (`quotes[(key, name)]`), so tags stay checkable."""
    driver = get_driver()
    ensure_schema(driver)
    db = get_settings().neo4j_database
    driver.execute_query(
        "MERGE (p:Paper {paper_id: $pid}) "
        "SET p.title = $title, p.license_class = $license, p.facts_format = $format, "
        "p.published = $published "
        "WITH p OPTIONAL MATCH (p)-[r]->() DELETE r",
        pid=paper_id,
        title=title,
        license=license_class,
        format=facts_format,
        published=published,
        database_=db,
    )
    quotes = quotes or {}
    for key, (rel, label) in FACT_EDGES.items():
        rows = [{"name": n, "quote": quotes.get((key, n), "")} for n in facts.get(key, []) if n]
        if rows:
            driver.execute_query(
                _cypher(
                    f"MATCH (p:Paper {{paper_id: $pid}}) UNWIND $rows AS row "
                    f"MERGE (e:{label}:__Entity__ {{name: row.name}}) "
                    f"MERGE (p)-[r:{rel}]->(e) SET r.quote = row.quote"
                ),
                pid=paper_id,
                rows=rows,
                database_=db,
            )
    _delete_orphans(driver)


def delete_paper_graph(paper_id: str) -> None:
    driver = get_driver()
    driver.execute_query(
        "MATCH (p:Paper {paper_id: $pid}) DETACH DELETE p",
        pid=paper_id,
        database_=get_settings().neo4j_database,
    )
    _delete_orphans(driver)


def _delete_orphans(driver: Driver) -> None:
    driver.execute_query(
        "MATCH (e:__Entity__) WHERE NOT (e)--() DELETE e",
        database_=get_settings().neo4j_database,
    )


def facts_format(paper_id: str) -> int | None:
    records, _, _ = get_driver().execute_query(
        "MATCH (p:Paper {paper_id: $pid}) RETURN p.facts_format AS f",
        pid=paper_id,
        database_=get_settings().neo4j_database,
    )
    return records[0]["f"] if records else None


def resolve_entities() -> int:
    """Merge spelling variants of technique names; returns the number of merged groups."""
    s = get_settings()
    resolver = FuzzyMatchResolver(
        get_driver(),
        filter_query=RESOLVED_LABELS,
        similarity_threshold=s.entity_similarity_threshold,
        neo4j_database=s.neo4j_database,
    )
    return asyncio.run(resolver.run()).number_of_created_nodes or 0


def fact_counts(key: str, paper_ids: list[str], limit: int = 15) -> list[tuple[str, int]]:
    """Number of readable papers per fact value, e.g. techniques → [("LLM agents", 11), ...]."""
    if not paper_ids:
        return []
    rel, label = FACT_EDGES[key]
    records, _, _ = get_driver().execute_query(
        _cypher(
            f"MATCH (p:Paper)-[:{rel}]->(e:{label}) WHERE p.paper_id IN $ids "
            "RETURN e.name AS name, count(DISTINCT p) AS n ORDER BY n DESC, name LIMIT $limit"
        ),
        ids=paper_ids,
        limit=limit,
        database_=get_settings().neo4j_database,
    )
    return [(r["name"], r["n"]) for r in records]


@dataclass(frozen=True)
class FactEdge:
    paper_id: str
    paper_title: str
    relation: str
    name: str
    label: str


def fact_edges(paper_ids: list[str]) -> list[FactEdge]:
    """All paper → fact edges of the readable papers (the knowledge graph)."""
    if not paper_ids:
        return []
    records, _, _ = get_driver().execute_query(
        "MATCH (p:Paper)-[r]->(e:__Entity__) WHERE p.paper_id IN $ids "
        "RETURN p.paper_id AS id, p.title AS title, type(r) AS rel, e.name AS name, "
        "[l IN labels(e) WHERE l <> '__Entity__'][0] AS label",
        ids=paper_ids,
        database_=get_settings().neo4j_database,
    )
    return [FactEdge(r["id"], r["title"], r["rel"], r["name"], r["label"]) for r in records]


@dataclass(frozen=True)
class PaperRow:
    paper_id: str
    title: str
    license_class: str
    facts: dict[str, list[str]]
    published: str | None = None
    quotes: dict[tuple[str, str], str] | None = None


def _match_filters(filters: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Cypher conditions requiring each filtered fact (keys from FACT_EDGES only)."""
    clauses, params = [], {}
    for i, (key, value) in enumerate(sorted(filters.items())):
        rel, label = FACT_EDGES[key]
        clauses.append(f"EXISTS {{ (p)-[:{rel}]->(:{label} {{name: $f{i}}}) }}")
        params[f"f{i}"] = value
    return "".join(f" AND {c}" for c in clauses), params


def matching_paper_ids(paper_ids: list[str], filters: dict[str, str]) -> list[str]:
    """The given papers that have every filtered fact, e.g. {"sdlc_phases": "testing"}."""
    if not paper_ids:
        return []
    if not filters:
        return list(paper_ids)
    where, params = _match_filters(filters)
    records, _, _ = get_driver().execute_query(
        _cypher(f"MATCH (p:Paper) WHERE p.paper_id IN $ids{where} RETURN p.paper_id AS id"),
        parameters_={"ids": paper_ids, **params},
        database_=get_settings().neo4j_database,
    )
    return [r["id"] for r in records]


def paper_rows(paper_ids: list[str]) -> list[PaperRow]:
    """Papers with all their extracted facts, newest arXiv id first."""
    if not paper_ids:
        return []
    records, _, _ = get_driver().execute_query(
        "MATCH (p:Paper) WHERE p.paper_id IN $ids "
        "OPTIONAL MATCH (p)-[r]->(e:__Entity__) "
        "RETURN p.paper_id AS id, p.title AS title, p.license_class AS license, "
        "p.published AS published, "
        "collect([[l IN labels(e) WHERE l <> '__Entity__'][0], e.name, r.quote]) AS facts "
        "ORDER BY id DESC",
        ids=paper_ids,
        database_=get_settings().neo4j_database,
    )
    by_label = {label: key for key, (_, label) in FACT_EDGES.items()}
    rows = []
    for r in records:
        facts: dict[str, list[str]] = {key: [] for key in FACT_EDGES}
        quotes: dict[tuple[str, str], str] = {}
        for label, name, quote in r["facts"]:
            if label in by_label and name:
                facts[by_label[label]].append(name)
                quotes[(by_label[label], name)] = quote or ""
        rows.append(
            PaperRow(
                r["id"], r["title"], r["license"] or "restricted", facts, r["published"], quotes
            )
        )
    return rows
