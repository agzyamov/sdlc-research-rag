"""Hybrid retrieval with cross-encoder reranking, assembled from LangChain building blocks:
`QdrantVectorStore.as_retriever` (dense + BM25, RRF) → `ContextualCompressionRetriever` with
`CrossEncoderReranker` (bge-reranker-v2-m3).

Access control (ADR-0007): OpenFGA `ListObjects` gives the principal's readable papers, which
become a Qdrant payload filter (pre-filter, so restricted chunks never reach the model);
`BatchCheck` re-checks the final sources (post-filter, defense in depth).
"""

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from sdlcrag.access.policy import get_access_policy
from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Principal
from sdlcrag.indexing.store import open_index
from sdlcrag.providers.embeddings import get_reranker


def build_retriever(
    store: QdrantVectorStore,
    *,
    candidates: int,
    top_k: int,
    qdrant_filter: models.Filter | None = None,
) -> ContextualCompressionRetriever:
    base = store.as_retriever(search_kwargs={"k": candidates, "filter": qdrant_filter})
    reranker = CrossEncoderReranker(model=get_reranker(), top_n=top_k)
    return ContextualCompressionRetriever(base_compressor=reranker, base_retriever=base)


def acl_filter(readable_paper_ids: list[str]) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.paper_id", match=models.MatchAny(any=readable_paper_ids)
            )
        ]
    )


def retrieve(query: str, principal: Principal, k: int | None = None) -> list[Document]:
    """Top-k reranked chunks the principal may read."""
    s = get_settings()
    access = get_access_policy()
    readable = access.readable_paper_ids(principal)
    if not readable:
        return []
    retriever = build_retriever(
        open_index().store,
        candidates=s.retrieval_candidates,
        top_k=k or s.retrieval_top_k,
        qdrant_filter=acl_filter(readable),
    )
    docs = retriever.invoke(query)
    allowed = access.can_read(principal, (str(d.metadata.get("paper_id")) for d in docs))
    return [d for d in docs if allowed.get(str(d.metadata.get("paper_id")), False)]
