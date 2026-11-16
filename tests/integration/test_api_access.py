"""Drill-through and landscape endpoints respect license-aware access (`pytest -m integration`).

Requires: docker services up, OpenFGA bootstrapped, an ingested corpus with extracted facts.
"""

import pytest
from fastapi.testclient import TestClient

from sdlcrag.core.config import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not get_settings().openfga_store_id:
        pytest.skip("OpenFGA not bootstrapped")
    from sdlcrag.api.main import app

    return TestClient(app)


def test_public_user_never_drills_into_restricted_papers(client: TestClient) -> None:
    alice = client.get("/api/papers", headers={"X-Demo-User": "alice"}).json()
    bob = client.get("/api/papers", headers={"X-Demo-User": "bob"}).json()
    if not bob:
        pytest.skip("no papers with extracted facts")
    assert all(p["license_class"] == "open" for p in alice)
    assert {p["paper_id"] for p in alice} < {p["paper_id"] for p in bob}


def test_filters_narrow_the_drill_through(client: TestClient) -> None:
    headers = {"X-Demo-User": "bob"}
    everything = client.get("/api/papers", headers=headers).json()
    if not everything:
        pytest.skip("no papers with extracted facts")
    phase = everything[0]["sdlc_phases"][0]
    narrowed = client.get("/api/papers", params={"phase": phase}, headers=headers).json()
    assert narrowed and all(phase in p["sdlc_phases"] for p in narrowed)
    counts = client.get("/api/landscape", params={"phase": phase}, headers=headers).json()
    assert [s["phase"] for s in counts["sdlc_phases"]].count(phase) == 1
