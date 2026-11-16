"""api: HTTP API for the web front end (`web/`, ADR-0019).

FastAPI app. `/api/chat` streams answers in assistant-ui's data-stream protocol via
`assistant-stream`. JSON endpoints serve the license-aware landscape, the knowledge graph,
the evaluation report and the demo principals.

Layer: presentation. May use: generation, extraction, evaluation, visualization, access, core.
"""
