"""Incremental indexing on an in-memory Qdrant with fake embeddings (no models, no network)."""

from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from qdrant_client import QdrantClient

from sdlcrag.indexing.store import (
    delete_paper,
    ensure_collection,
    get_record_manager,
    get_vector_store,
    index_paper_chunks,
    indexed_papers,
)

DIM = 16
COLLECTION = "test"


@pytest.fixture
def env(tmp_path: Path):
    client = QdrantClient(":memory:")
    ensure_collection(client, COLLECTION, DIM)
    store = get_vector_store(client, COLLECTION, DeterministicFakeEmbedding(size=DIM))
    manager = get_record_manager(COLLECTION, db_url=f"sqlite:///{tmp_path / 'rm.sqlite'}")
    return client, store, manager


def chunks(pid: str, version: int, texts: list[str]) -> list[Document]:
    meta = {"paper_id": pid, "version": version, "published": "2026-11-12"}
    return [Document(page_content=t, metadata=meta) for t in texts]


def test_reindexing_same_content_is_skipped(env) -> None:
    _, store, manager = env
    first = index_paper_chunks(chunks("p1", 1, ["a", "b"]), store, manager)
    again = index_paper_chunks(chunks("p1", 1, ["a", "b"]), store, manager)
    assert first["num_added"] == 2
    assert again["num_added"] == 0
    assert again["num_skipped"] == 2


def test_new_version_replaces_only_changed_chunks(env) -> None:
    client, store, manager = env
    index_paper_chunks(chunks("p1", 1, ["intro", "method"]), store, manager)
    result = index_paper_chunks(chunks("p1", 2, ["intro", "method v2"]), store, manager)
    # version is part of the metadata, so all chunks of v2 are new and v1's are cleaned up
    assert result["num_added"] == 2
    assert result["num_deleted"] == 2
    assert indexed_papers(client, COLLECTION)["p1"].version == 2


def test_delete_paper_removes_all_chunks(env) -> None:
    client, store, manager = env
    index_paper_chunks(chunks("p1", 1, ["a", "b"]), store, manager)
    index_paper_chunks(chunks("p2", 1, ["c"]), store, manager)
    assert delete_paper("p1", store, manager) == 2
    assert set(indexed_papers(client, COLLECTION)) == {"p2"}
