"""RAG quality regression gate (`pytest -m eval`): runs the real pipeline and the LLM judge.

Needs the services, an indexed corpus, OpenFGA and the gateway (VPN). Costs about $1 per run.
"""

from pathlib import Path

import pytest

from sdlcrag.evaluation.dataset import load_golden

pytestmark = pytest.mark.eval
GOLDEN = Path(__file__).resolve().parents[2] / "eval" / "golden_qa.jsonl"


def test_rag_meets_quality_targets() -> None:
    from sdlcrag.evaluation.runner import THRESHOLDS, run_evaluation

    report = run_evaluation(load_golden(GOLDEN))
    for metric, target in THRESHOLDS.items():
        assert report.summary[metric] >= target, f"{metric}: {report.summary[metric]} < {target}"
    assert report.summary.get("ACL leaks", 0) == 0
