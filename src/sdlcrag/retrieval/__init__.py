"""retrieval: permission-aware hybrid retrieval.

Pipeline: ACL pre-filter, then Qdrant dense+BM25 with RRF fusion, then cross-encoder rerank.

Layer: domain. May use: access, indexing, providers, core.
"""
