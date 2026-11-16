"""Embedding and reranking model factories (ADR-0005, ADR-0006), via LangChain integrations."""

from functools import lru_cache
from typing import TYPE_CHECKING

from sdlcrag.core.config import get_settings

if TYPE_CHECKING:
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder
    from langchain_core.embeddings import Embeddings
    from langchain_qdrant import FastEmbedSparse


@lru_cache
def get_embeddings() -> "Embeddings":
    """Dense embeddings: Qwen3-Embedding via sentence-transformers (langchain-huggingface)."""
    from langchain_huggingface import HuggingFaceEmbeddings

    s = get_settings()
    return HuggingFaceEmbeddings(
        model_name=s.embedding_model,
        model_kwargs={"device": s.device},
        encode_kwargs={"normalize_embeddings": True},
        # Qwen3-Embedding uses an instruction prompt for queries only.
        query_encode_kwargs={"prompt_name": "query", "normalize_embeddings": True},
    )


@lru_cache
def get_sparse_embeddings() -> "FastEmbedSparse":
    """Sparse BM25 embeddings via FastEmbed (langchain-qdrant)."""
    from langchain_qdrant import FastEmbedSparse

    return FastEmbedSparse(model_name=get_settings().sparse_model)


@lru_cache
def get_reranker() -> "HuggingFaceCrossEncoder":
    """Cross-encoder bge-reranker-v2-m3 (ADR-0006) via langchain-community."""
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder

    s = get_settings()
    return HuggingFaceCrossEncoder(model_name=s.reranker_model, model_kwargs={"device": s.device})
