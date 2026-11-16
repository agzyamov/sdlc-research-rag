"""Golden Q&A set (eval/golden_qa.jsonl) as a DeepEval `EvaluationDataset` (ADR-0008).

Project-specific fields (id, topic, principal, category, expected paper ids, metadata ground
truth, review status) live in each golden's `additional_metadata`.
"""

from pathlib import Path

from deepeval.dataset import EvaluationDataset, Golden


def load_golden(path: Path, *, verified_only: bool = False) -> list[Golden]:
    dataset = EvaluationDataset()
    dataset.add_goldens_from_jsonl_file(str(path))
    goldens = [g for g in dataset.goldens if isinstance(g, Golden)]
    if verified_only:
        goldens = [g for g in goldens if (g.additional_metadata or {}).get("status") == "verified"]
    return goldens
