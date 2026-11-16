"""ingestion: arXiv harvest (initial + OAI-PMH incremental) → Docling parse → chunk → enrich →
incremental index + ACL registration.

Layer: application. May use: access, indexing, providers, core.
ADRs: 0003 (Docling), 0013 (dataset).
"""
