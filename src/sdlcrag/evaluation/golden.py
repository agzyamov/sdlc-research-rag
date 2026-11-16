"""Golden set synthesis with DeepEval's `Synthesizer` (ADR-0008).

Questions and reference answers are generated from chunks of **open-licensed** papers only:
the golden set is committed to a public repository, and answers derived from papers under the
arXiv non-exclusive license would redistribute their content.
"""

import json
from pathlib import Path

from deepeval.synthesizer import Synthesizer
from qdrant_client import models

from sdlcrag.core.config import get_settings
from sdlcrag.evaluation.judge import GatewayJudge
from sdlcrag.indexing.store import get_client, paper_abstracts

CHUNKS_PER_CONTEXT = 3
MIN_CHUNK_CHARS = 400

# Hand-written check that a public user gets nothing from a restricted paper.
ACL_GOLDEN = {
    "input": "How robust is CodeQL taint tracking against LLM-rewritten vulnerable code?",
    "expected_output": (
        "The system must not answer from the restricted CodeQL paper for a public user; it "
        "should say the available sources do not cover this."
    ),
    "additional_metadata": {
        "id": "acl-001",
        "principal": "alice",
        "category": "acl",
        "expected_paper_ids": [],
        "restricted_paper_ids": ["2611.17123"],
        "status": "verified",
    },
}


def paper_contexts() -> dict[str, list[str]]:
    """paper_id → a few substantial chunks (abstract + body + a figure if any), open papers only."""
    s = get_settings()
    client = get_client()
    open_ids = [
        str((p.payload or {}).get("metadata", {}).get("paper_id"))
        for p in client.scroll(
            s.qdrant_collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.modality", match=models.MatchValue(value="abstract")
                    ),
                    models.FieldCondition(
                        key="metadata.license_class", match=models.MatchValue(value="open")
                    ),
                ]
            ),
            limit=10_000,
            with_payload=["metadata.paper_id"],
            with_vectors=False,
        )[0]
    ]
    contexts: dict[str, list[str]] = {}
    for row in paper_abstracts(client, s.qdrant_collection, open_ids):
        points = client.scroll(
            s.qdrant_collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.paper_id", match=models.MatchValue(value=row.paper_id)
                    ),
                    models.FieldCondition(
                        key="metadata.modality", match=models.MatchAny(any=["text", "image"])
                    ),
                ]
            ),
            limit=500,
            with_payload=True,
            with_vectors=False,
        )[0]
        texts = [str((p.payload or {}).get("page_content", "")) for p in points]
        body = sorted((t for t in texts if len(t) >= MIN_CHUNK_CHARS), key=len, reverse=True)
        contexts[row.paper_id] = [row.text, *body[: CHUNKS_PER_CONTEXT - 1]]
    return contexts


def synthesize_goldens(path: Path) -> int:
    """Generate one golden per open paper with DeepEval and write them (plus the ACL check).

    Only the question, the reference answer and the source paper id are stored, not chunk text.
    """
    contexts = paper_contexts()
    synthesizer = Synthesizer(model=GatewayJudge("judge"), async_mode=False)
    rows = [ACL_GOLDEN]
    for pid, chunks in contexts.items():
        goldens = synthesizer.generate_goldens_from_contexts(
            contexts=[chunks], include_expected_output=True, max_goldens_per_context=1
        )
        for g in goldens:
            rows.append(
                {
                    "input": g.input,
                    "expected_output": g.expected_output,
                    "additional_metadata": {
                        "id": f"syn-{pid}",
                        "principal": "admin",
                        "category": "synthetic",
                        "expected_paper_ids": [pid],
                        "status": "synthetic",  # LLM-generated, reviewed before use
                    },
                }
            )
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    return len(rows)
