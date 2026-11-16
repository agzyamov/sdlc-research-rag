"""Shared domain models used across modules (the only cross-module data contract)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Classification(StrEnum):
    """Access class derived from the paper's license (see data/corpus.yaml)."""

    OPEN = "open"  # Creative Commons / public domain: may be shown to anyone
    RESTRICTED = "restricted"  # arXiv non-exclusive license: internal users only


class Modality(StrEnum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class SdlcPhase(StrEnum):
    """SDLC phases in lifecycle order (the order defines their numbers)."""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "code_review"
    DEPLOYMENT = "deployment_operations"
    MAINTENANCE = "maintenance_evolution"
    PROCESS = "process_management"

    @property
    def number(self) -> int:
        return list(SdlcPhase).index(self) + 1

    @property
    def display_name(self) -> str:
        return PHASE_TITLES[self]


PHASE_TITLES = {
    SdlcPhase.REQUIREMENTS: "Requirements",
    SdlcPhase.DESIGN: "Design",
    SdlcPhase.IMPLEMENTATION: "Implementation",
    SdlcPhase.TESTING: "Testing",
    SdlcPhase.REVIEW: "Code review",
    SdlcPhase.DEPLOYMENT: "Deployment & operations",
    SdlcPhase.MAINTENANCE: "Maintenance & evolution",
    SdlcPhase.PROCESS: "Process & management",
}


class CorpusFilter(BaseModel):
    """Which arXiv papers belong to the corpus (data/corpus.yaml)."""

    categories: list[str] = Field(default_factory=lambda: ["cs.SE"])
    since: date = date(2023, 1, 1)
    keywords: list[str] = Field(default_factory=list)


class LicensePolicy(BaseModel):
    """License URL → access class (data/corpus.yaml `license_policy`)."""

    open: list[str] = Field(default_factory=list)
    restricted: list[str] = Field(default_factory=list)
    default: Classification = Classification.RESTRICTED


class CorpusWindow(BaseModel):
    """Rolling window over the filtered papers: keep only the newest N."""

    max_papers: int = 20
    dev_max_papers: int = 20


def arxiv_abs_url(paper_id: str, version: int | None = None) -> str:
    """arXiv abstract page; without a version it shows the latest one."""
    return f"https://arxiv.org/abs/{paper_id}" + (f"v{version}" if version else "")


class Paper(BaseModel):
    paper_id: str = Field(description="arXiv id without version, e.g. '2611.17316'")
    version: int = 1
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    categories: list[str] = Field(default_factory=list)
    published: date | None = None
    updated: date | None = None
    license: str | None = None
    classification: Classification = Classification.RESTRICTED
    withdrawn: bool = False

    @property
    def abs_url(self) -> str:
        return arxiv_abs_url(self.paper_id, self.version)

    @property
    def pdf_url(self) -> str:
        return f"https://arxiv.org/pdf/{self.paper_id}v{self.version}"


class Chunk(BaseModel):
    chunk_id: str
    paper_id: str
    text: str
    content_hash: str
    section: str | None = None
    modality: Modality = Modality.TEXT
    page: int | None = None
    metadata: dict[str, str | int | float | None] = Field(default_factory=dict)


class Principal(BaseModel):
    """The user on whose behalf retrieval happens (ACL subject)."""

    user_id: str


class DemoPrincipal(BaseModel):
    """A demo user from data/corpus.yaml `principals` (selectable in the UI)."""

    id: str
    description: str = ""
    groups: list[str] = Field(default_factory=list)


class Source(BaseModel):
    """A retrieved chunk as shown to the model and the user, numbered [n]."""

    number: int
    paper_id: str
    title: str
    section: str | None = None
    page: int | None = None
    url: str | None = None
    license_class: str | None = None
    text: str


class Answer(BaseModel):
    question: str
    text: str  # inline citations as [n]
    cited: list[int] = Field(default_factory=list)  # source numbers actually used
    sources: list[Source] = Field(default_factory=list)


class FactEvidence(BaseModel):
    """A verbatim quote from the abstract supporting one extracted fact ("" = none found)."""

    kind: str  # sdlc_phases | techniques | models | benchmarks
    name: str
    quote: str = ""


class PaperFacts(BaseModel):
    """Structured facts extracted from one paper (feeds charts and the graph)."""

    paper_id: str
    evidence: list[FactEvidence] = Field(default_factory=list)
    sdlc_phases: list[SdlcPhase] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)  # e.g. "RAG", "agentic", "fine-tuning"
    models: list[str] = Field(default_factory=list)  # e.g. "GPT-4o", "Claude", "CodeLlama"
    benchmarks: list[str] = Field(default_factory=list)  # e.g. "SWE-bench Verified", "HumanEval"


class FacetCount(BaseModel):
    """One slice of a pie/bar chart, e.g. facet='sdlc_phase', label='testing', count=412."""

    facet: str
    label: str
    count: int


class Triple(BaseModel):
    """Extracted relation for the knowledge graph, e.g. (paper, EVALUATED_ON, SWE-bench)."""

    subject: str
    subject_type: str
    subject_label: str | None = None  # display name when `subject` is an id (paper title)
    predicate: str
    object: str
    object_type: str
    source_chunk_id: str | None = None
