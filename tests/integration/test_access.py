"""License-aware access against the live OpenFGA store and Qdrant index (`pytest -m integration`).

Requires: docker services up, infra/openfga/bootstrap.sh done, and an ingested corpus.
"""

import pytest

from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Principal

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def setup():
    if not get_settings().openfga_store_id:
        pytest.skip("OpenFGA not bootstrapped")
    from sdlcrag.access.policy import get_access_policy
    from sdlcrag.indexing.store import get_client, indexed_papers

    papers = indexed_papers(get_client(), get_settings().qdrant_collection)
    if not papers:
        pytest.skip("no indexed papers")
    return get_access_policy(), papers


def test_public_user_reads_only_open_papers(setup) -> None:
    access, papers = setup
    readable = set(access.readable_paper_ids(Principal(user_id="alice")))
    open_ids = {pid for pid, p in papers.items() if p.license_class == "open"}
    assert readable & set(papers) == open_ids


def test_internal_user_reads_everything(setup) -> None:
    access, papers = setup
    assert set(papers) <= set(access.readable_paper_ids(Principal(user_id="bob")))


def test_no_restricted_chunk_reaches_a_public_user(setup) -> None:
    from sdlcrag.retrieval.retriever import retrieve

    _, papers = setup
    restricted = [p for p in papers.values() if p.license_class == "restricted"]
    if not restricted:
        pytest.skip("no restricted papers indexed")
    docs = retrieve("benchmark evaluation of LLM agents", Principal(user_id="alice"), k=10)
    assert all(d.metadata["license_class"] == "open" for d in docs)
