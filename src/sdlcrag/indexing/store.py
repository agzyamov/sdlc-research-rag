"""Qdrant hybrid store and LangChain RecordManager wiring (glue over OSS building blocks)."""

import hashlib
import json
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.indexing import IndexingResult, RecordManager, index
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models

from sdlcrag.core.config import get_settings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_qdrant import SparseEmbeddings

DENSE = "dense"
SPARSE = "sparse"
SOURCE_KEY = "paper_id"  # RecordManager group: all chunks of one paper
PAYLOAD_INDEXES = {
    "metadata.paper_id": models.PayloadSchemaType.KEYWORD,
    "metadata.license_class": models.PayloadSchemaType.KEYWORD,
    "metadata.categories": models.PayloadSchemaType.KEYWORD,
    "metadata.published": models.PayloadSchemaType.KEYWORD,  # ISO date string
    "metadata.modality": models.PayloadSchemaType.KEYWORD,
}


def _chunk_key(doc: Document) -> str:
    """Content key for LangChain's RecordManager: SHA-256 over text + metadata, formatted as a
    UUID because Qdrant point ids must be UUIDs or integers."""
    payload = json.dumps([doc.page_content, doc.metadata], sort_keys=True, default=str)
    return str(uuid.UUID(hashlib.sha256(payload.encode()).hexdigest()[:32]))


@dataclass(frozen=True)
class IndexedPaper:
    version: int
    published: str
    index_format: int = 1
    license_class: str = "restricted"

    def stale(self, latest_version: int, current_format: int) -> bool:
        return self.version < latest_version or self.index_format < current_format


def get_client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url)


@dataclass(frozen=True)
class OpenIndex:
    store: QdrantVectorStore
    manager: RecordManager
    client: QdrantClient


@lru_cache
def open_index() -> OpenIndex:
    """The configured hybrid index (models loaded once per process)."""
    from sdlcrag.providers.embeddings import get_embeddings, get_sparse_embeddings

    s = get_settings()
    client = get_client()
    embedding = get_embeddings()
    ensure_collection(client, s.qdrant_collection, dim=len(embedding.embed_query("dim probe")))
    ensure_payload_indexes(client, s.qdrant_collection)
    store = get_vector_store(client, s.qdrant_collection, embedding, get_sparse_embeddings())
    return OpenIndex(store, get_record_manager(s.qdrant_collection), client)


def ensure_collection(client: QdrantClient, collection: str, dim: int) -> None:
    """Create the hybrid collection (dense int8-quantized on disk + BM25 sparse) if missing."""
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config={
            DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE, on_disk=True)
        },
        sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, always_ram=True)
        ),
    )
    ensure_payload_indexes(client, collection)


def ensure_payload_indexes(client: QdrantClient, collection: str) -> None:
    """Create any missing payload index (idempotent; lets new fields be added later)."""
    existing = set((client.get_collection(collection).payload_schema or {}).keys())
    for field, schema in PAYLOAD_INDEXES.items():
        if field not in existing:
            client.create_payload_index(collection, field_name=field, field_schema=schema)


def get_vector_store(
    client: QdrantClient,
    collection: str,
    embedding: "Embeddings",
    sparse_embedding: "SparseEmbeddings | None" = None,
) -> QdrantVectorStore:
    """Hybrid (dense + BM25, RRF fusion) when a sparse model is given, else dense-only."""
    mode = RetrievalMode.HYBRID if sparse_embedding is not None else RetrievalMode.DENSE
    return QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=embedding,
        sparse_embedding=sparse_embedding,
        retrieval_mode=mode,
        vector_name=DENSE,
        sparse_vector_name=SPARSE,
    )


def get_record_manager(collection: str, db_url: str | None = None) -> RecordManager:
    from langchain_classic.indexes import SQLRecordManager

    manager = SQLRecordManager(
        f"qdrant/{collection}", db_url=db_url or get_settings().record_manager_db_url
    )
    manager.create_schema()
    return manager


def index_paper_chunks(
    chunks: list[Document], store: QdrantVectorStore, manager: RecordManager
) -> IndexingResult:
    """Upsert one paper's chunks; unchanged chunks are skipped and stale ones of the same
    paper (e.g. from an older version) are deleted by LangChain's incremental cleanup."""
    return index(
        chunks,
        manager,
        store,
        cleanup="incremental",
        source_id_key=SOURCE_KEY,
        key_encoder=_chunk_key,
    )


def delete_paper(paper_id: str, store: QdrantVectorStore, manager: RecordManager) -> int:
    """Remove all chunks of a paper (withdrawn or evicted from the window)."""
    keys = manager.list_keys(group_ids=[paper_id])
    if keys:
        ids: list[int | str] = list(keys)
        store.delete(ids=ids)
        manager.delete_keys(keys)
    return len(keys)


def indexed_papers(client: QdrantClient, collection: str) -> dict[str, IndexedPaper]:
    """paper_id → indexed version/published, read from the store's payloads."""
    if not client.collection_exists(collection):
        return {}
    papers: dict[str, IndexedPaper] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection,
            limit=1000,
            offset=offset,
            with_vectors=False,
            with_payload=[
                "metadata.paper_id",
                "metadata.version",
                "metadata.published",
                "metadata.index_format",
                "metadata.license_class",
            ],
        )
        for point in points:
            meta = (point.payload or {}).get("metadata", {})
            if pid := meta.get("paper_id"):
                papers[pid] = IndexedPaper(
                    int(meta.get("version", 1)),
                    str(meta.get("published")),
                    int(meta.get("index_format", 1)),
                    str(meta.get("license_class", "restricted")),
                )
        if offset is None:
            return papers


def _abstracts_filter(paper_ids: list[str] | None) -> models.Filter:
    must: list[models.Condition] = [
        models.FieldCondition(key="metadata.modality", match=models.MatchValue(value="abstract"))
    ]
    if paper_ids is not None:
        must.append(
            models.FieldCondition(key="metadata.paper_id", match=models.MatchAny(any=paper_ids))
        )
    return models.Filter(must=must)


@dataclass(frozen=True)
class PaperAbstract:
    paper_id: str
    title: str
    text: str
    license_class: str
    published: str | None = None


def paper_abstracts(
    client: QdrantClient, collection: str, paper_ids: list[str] | None = None
) -> list[PaperAbstract]:
    """Abstract points (one per paper): the input of fact extraction."""
    rows: list[PaperAbstract] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection,
            scroll_filter=_abstracts_filter(paper_ids),
            limit=500,
            offset=offset,
            with_vectors=False,
            with_payload=True,
        )
        for point in points:
            payload = point.payload or {}
            meta = payload.get("metadata", {})
            rows.append(
                PaperAbstract(
                    paper_id=str(meta.get("paper_id")),
                    title=str(meta.get("title", "")),
                    text=str(payload.get("page_content", "")),
                    license_class=str(meta.get("license_class", "restricted")),
                    published=meta.get("published"),
                )
            )
        if offset is None:
            return rows
