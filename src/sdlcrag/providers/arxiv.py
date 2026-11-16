"""arXiv access (ADR-0013), built on OSS clients:

- OAI-PMH harvesting with `oaipmh-scythe` (paging, retries, Retry-After handling)
- PDF download with `httpx` (mirror first, arxiv.org fallback), throttled by `pyrate-limiter`

arXiv terms of use: https://info.arxiv.org/help/api/tos.html
"""

from collections.abc import Iterator
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
from oaipmh_scythe import NoRecordsMatch, Scythe
from oaipmh_scythe.config import HTTPConfig, RetryConfig
from oaipmh_scythe.models import Record
from pyrate_limiter import Limiter, Rate

from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Paper

OAI_PMH_URL = "https://oaipmh.arxiv.org/oai"
PDF_URL = "https://arxiv.org/pdf/{paper_id}v{version}"
# Public bulk mirror (Kaggle arXiv dataset); no rate limit, may lag for the newest papers.
BULK_PDF_URL = (
    "https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{yymm}/{paper_id}v{version}.pdf"
)


def paper_from_metadata(meta: dict[str, list[Any]]) -> Paper:
    """Map an arXivRaw record (as flattened by oaipmh-scythe) to a Paper.

    arXivRaw has one <version> per revision, so `date` holds one entry per version.
    """
    dates = [parsedate_to_datetime(d).date() for d in meta.get("date", []) if d]
    sizes = meta.get("size", [])
    first = lambda key: (meta.get(key) or [""])[0] or ""  # noqa: E731
    return Paper(
        paper_id=first("id"),
        version=max(len(dates), 1),
        title=" ".join(first("title").split()),
        authors=[a.strip() for a in first("authors").split(",") if a.strip()],
        abstract=" ".join(first("abstract").split()),
        categories=first("categories").split(),
        published=dates[0] if dates else None,
        updated=dates[-1] if dates else None,
        license=first("license") or None,
        withdrawn=bool(sizes) and sizes[-1] == "0kb",
    )


def harvest(set_spec: str, from_date: date, until: date | None = None) -> Iterator[Paper]:
    """Yield papers whose arXiv metadata changed in [from_date, until] (new, revised, withdrawn)."""
    s = get_settings()
    with Scythe(
        OAI_PMH_URL,
        http_config=HTTPConfig(user_agent=s.http_user_agent, timeout=120),
        retry_config=RetryConfig(
            max_retries=5,
            retry_status_codes={429, 500, 502, 503},
            default_retry_after=10,
            retry_on_transport_error=True,
        ),
    ) as client:
        try:
            records = client.list_records(
                from_=from_date.isoformat(),
                until=until.isoformat() if until else None,
                metadata_prefix="arXivRaw",
                set_=set_spec,
                ignore_deleted=True,
            )
            for record in records:
                metadata = getattr(record, "metadata", None)
                if metadata:
                    yield paper_from_metadata(metadata)
        except NoRecordsMatch:
            return


def fetch_paper(paper_id: str) -> Paper:
    """Fetch one paper's current metadata (used when retrying a paper outside a fresh harvest)."""
    with Scythe(
        OAI_PMH_URL, http_config=HTTPConfig(user_agent=get_settings().http_user_agent)
    ) as client:
        record = client.get_record(
            identifier=f"oai:arXiv.org:{paper_id}", metadata_prefix="arXivRaw"
        )
        if not isinstance(record, Record) or not record.metadata:
            raise LookupError(f"arXiv record {paper_id} not found or deleted")
        return paper_from_metadata(record.metadata)


class PdfDownloader:
    """Download paper PDFs: public bulk mirror first, arxiv.org as fallback.

    Throttling (arXiv: <= 1 request / 3 s) is pyrate-limiter's job, retries httpx's transport
    and the orchestrator's retry policy.
    """

    def __init__(self) -> None:
        s = get_settings()
        interval_ms = int(s.arxiv_min_interval_s * 1000)
        self._arxiv_limiter = Limiter(Rate(1, interval_ms))
        self._client = httpx.Client(
            headers={"User-Agent": s.http_user_agent},
            timeout=120.0,
            follow_redirects=True,
            transport=httpx.HTTPTransport(retries=3),
        )

    def download(self, paper: Paper, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{paper.paper_id}v{paper.version}.pdf"
        if dest.exists():
            return dest
        yymm = paper.paper_id.split(".")[0]
        mirror = BULK_PDF_URL.format(yymm=yymm, paper_id=paper.paper_id, version=paper.version)
        response = self._client.get(mirror)
        if response.status_code != httpx.codes.OK:
            self._arxiv_limiter.try_acquire("arxiv")  # blocks until the 3 s slot is free
            response = self._client.get(
                PDF_URL.format(paper_id=paper.paper_id, version=paper.version)
            )
            response.raise_for_status()
        dest.write_bytes(response.content)
        return dest

    def close(self) -> None:
        self._client.close()


def today() -> date:
    return datetime.now().date()
