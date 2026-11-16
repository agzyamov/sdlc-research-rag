from datetime import date
from pathlib import Path

import pytest

from sdlcrag.core.config import Settings
from sdlcrag.evaluation.dataset import load_golden
from sdlcrag.ingestion.pipeline import load_corpus_filter, load_corpus_window

ROOT = Path(__file__).resolve().parents[2]


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_QDRANT_COLLECTION", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings(_env_file=None)
    assert s.qdrant_collection == "test"
    assert s.anthropic_api_key is not None
    assert s.anthropic_api_key.get_secret_value() == "sk-test"
    assert s.record_manager_db_url == "sqlite:///data/index/record_manager.sqlite"


def test_corpus_yaml_is_valid() -> None:
    corpus = load_corpus_filter(ROOT / "data" / "corpus.yaml")
    assert corpus.categories == ["cs.SE"]
    assert corpus.since == date(2023, 1, 1)
    assert "LLM" in corpus.keywords
    window = load_corpus_window(ROOT / "data" / "corpus.yaml")
    assert (window.dev_max_papers, window.max_papers) == (20, 20)  # token budget: no 2k run


def test_golden_set_is_valid() -> None:
    items = load_golden(ROOT / "eval" / "golden_qa.jsonl")
    assert len(items) >= 10
    ids = [(g.additional_metadata or {})["id"] for g in items]
    assert len(set(ids)) == len(items)
