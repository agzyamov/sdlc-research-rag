"""orchestration: Dagster assets, schedules and the code location (ADR-0016, ADR-0017).

Composes the plain-function modules (ingestion, extraction, access, indexing) into the corpus
pipeline: corpus_plan → paper_index → paper_facts.

Layer: orchestration (below app | cli, above the application modules). May use: any lower layer.
"""
