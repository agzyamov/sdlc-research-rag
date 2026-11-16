"""indexing: Qdrant hybrid vector store + LangChain RecordManager for incremental updates.

Built on OSS blocks: `langchain-qdrant` (dense + BM25 hybrid, RRF fusion), LangChain's Indexing
API (`index()` + `SQLRecordManager`: content-hash dedup, per-paper cleanup). No collection rebuild.

Layer: infrastructure. May use: providers, core. The only module allowed to talk to Qdrant.
ADR: 0004.
"""
