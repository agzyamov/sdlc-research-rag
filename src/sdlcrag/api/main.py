"""FastAPI app: `uv run sdlcrag serve` (dev: the Vite server proxies /api to it).

Identity (demo): the web UI sends the selected demo user in the `X-Demo-User` header, which
must be one of data/corpus.yaml `principals`. This is a demo user switcher, not
authentication. A deployment puts an identity proxy (OIDC) in front and derives the principal
from the verified token instead; everything below the header lookup stays the same.
"""

from typing import Annotated, Any

from assistant_stream import RunController, create_run
from assistant_stream.serialization import DataStreamResponse
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from sdlcrag.access.policy import demo_principals
from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Answer, DemoPrincipal, FactEvidence, Principal, arxiv_abs_url
from sdlcrag.evaluation.runner import EvalReport, load_latest_report
from sdlcrag.extraction.extractors import (
    corpus_size,
    knowledge_graph,
    paper_count,
    papers_with_facts,
    research_landscape,
)
from sdlcrag.generation.graph import astream_answer
from sdlcrag.visualization.charts import phase_series, top_series
from sdlcrag.visualization.graph import graph_json

app = FastAPI(
    title="SDLC Research RAG API",
    version="1",
    # Operation ids = function names, so generated client functions read `getLandscape`-style.
    generate_unique_id_function=lambda route: route.name,
)


# Response models: the HTTP contract. contracts/openapi.json is generated from them, and the
# web app's TypeScript types are generated from that file (ADR-0019).
class PhaseSlice(BaseModel):
    phase: str
    label: str
    count: int


class Slice(BaseModel):
    label: str
    count: int


class Landscape(BaseModel):
    total_papers: int  # readable papers in scope: the base of every count
    corpus_papers: int  # all indexed papers (count only): "3 of 20; 17 internal-only"
    sdlc_phases: list[PhaseSlice]
    techniques: list[Slice]
    models: list[Slice]
    benchmarks: list[Slice]


class PaperSummary(BaseModel):
    """A paper behind a chart slice, bar or graph node (drill-through)."""

    paper_id: str
    title: str
    url: str
    license_class: str
    published: str | None  # first-submission date (ISO), when known
    evidence: list[FactEvidence]  # verbatim abstract quote per fact ("" = none found)
    sdlc_phases: list[str]
    techniques: list[str]
    models: list[str]
    benchmarks: list[str]


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    degree: int


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphData(BaseModel):
    total_papers: int  # readable papers; papers without extracted facts have no node
    nodes: list[GraphNode]
    edges: list[GraphEdge]


DemoUser = Annotated[str, Header(alias="X-Demo-User")]


def _principal(user: str) -> Principal:
    known = {p.id for p in demo_principals(get_settings().corpus_path)}
    if user not in known:
        raise HTTPException(status_code=403, detail=f"unknown demo user {user!r}")
    return Principal(user_id=user)


@app.get("/api/principals")
def principals() -> list[DemoPrincipal]:
    return demo_principals(get_settings().corpus_path)


class ChatRequest(BaseModel):
    """assistant-ui data-stream request (extra fields such as `tools` are ignored)."""

    messages: list[dict[str, Any]]


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content") or message.get("parts") or []
        if isinstance(content, str):
            return content
        return "".join(p.get("text", "") for p in content if p.get("type") == "text")
    return ""


def _source_title(answer: Answer, number: int) -> str:
    s = next(s for s in answer.sources if s.number == number)
    where = ", ".join(x for x in (s.section, f"p. {s.page}" if s.page else None) if x)
    restricted = " · restricted" if s.license_class == "restricted" else ""
    return f"[{number}] {s.title}" + (f" · {where}" if where else "") + restricted


@app.post("/api/chat")
async def chat(request: ChatRequest, x_demo_user: DemoUser) -> DataStreamResponse:
    """Answer the latest user message (single-turn RAG), streaming text then cited sources."""
    principal = _principal(x_demo_user)
    question = _last_user_text(request.messages)
    if not question:
        raise HTTPException(status_code=422, detail="no user message")

    async def run(controller: RunController) -> None:
        async for item in astream_answer(question, principal):
            if isinstance(item, str):
                controller.append_text(item)
                continue
            for number in item.cited:
                src = next(s for s in item.sources if s.number == number)
                if src.url:
                    controller.add_source(
                        id=str(number), url=src.url, title=_source_title(item, number)
                    )

    return DataStreamResponse(create_run(run))


class FactFilters(BaseModel):
    """Query filters shared by the landscape and the drill-through (all optional)."""

    phase: str | None = None
    technique: str | None = None
    model: str | None = None
    benchmark: str | None = None

    def as_dict(self) -> dict[str, str]:
        given = {
            "sdlc_phases": self.phase,
            "techniques": self.technique,
            "models": self.model,
            "benchmarks": self.benchmark,
        }
        return {key: value for key, value in given.items() if value}


class PaperFilters(FactFilters):
    paper: str | None = None  # one readable paper by arXiv id


@app.get("/api/landscape")
def landscape(x_demo_user: DemoUser, filters: Annotated[FactFilters, Query()]) -> Landscape:
    """Papers per SDLC phase (lifecycle order) and top techniques/models/benchmarks, over the
    readable papers; optional filters cross-filter it (e.g. phase=testing)."""
    principal = _principal(x_demo_user)
    facts = research_landscape(principal, filters.as_dict())
    return Landscape.model_validate(
        {
            "total_papers": paper_count(principal, filters.as_dict()),
            "corpus_papers": corpus_size(),
            "sdlc_phases": phase_series(facts["sdlc_phases"]),
            **{key: top_series(facts[key]) for key in ("techniques", "models", "benchmarks")},
        }
    )


@app.get("/api/papers")
def papers(x_demo_user: DemoUser, filters: Annotated[PaperFilters, Query()]) -> list[PaperSummary]:
    """Drill-through: the readable papers having every given fact (none = all readable);
    `paper` selects one readable paper by arXiv id."""
    rows = papers_with_facts(_principal(x_demo_user), filters.as_dict(), filters.paper)
    return [
        PaperSummary(
            paper_id=r.paper_id,
            title=r.title,
            url=arxiv_abs_url(r.paper_id),
            license_class=r.license_class,
            published=r.published,
            evidence=[
                FactEvidence(kind=kind, name=name, quote=quote)
                for (kind, name), quote in (r.quotes or {}).items()
            ],
            **r.facts,
        )
        for r in rows
    ]


@app.get("/api/graph")
def graph(x_demo_user: DemoUser) -> GraphData:
    """Knowledge graph of the papers this user may read (nodes with type and degree)."""
    principal = _principal(x_demo_user)
    return GraphData.model_validate(
        {**graph_json(knowledge_graph(principal)), "total_papers": paper_count(principal)}
    )


@app.get("/api/eval")
def evaluation() -> EvalReport:
    """Latest evaluation report (written by `sdlcrag eval`); 404 before the first run."""
    report = load_latest_report(get_settings().reports_dir)
    if report is None:
        raise HTTPException(status_code=404, detail="no evaluation report yet")
    return report
