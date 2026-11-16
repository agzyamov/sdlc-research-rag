"""LLM factory: per-role backends (no network calls; only client construction)."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from sdlcrag.core.config import get_settings
from sdlcrag.providers.llm import get_llm


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)  # ignore the developer's .env file
    # ...and anything already loaded from it into the environment (DeepEval loads .env on import)
    for var in list(os.environ):
        if var.startswith(("SDLCRAG_", "ANTHROPIC_")):
            monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_local_backend_uses_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_EXTRACTION_BACKEND", "local")
    monkeypatch.setenv("SDLCRAG_EXTRACTION_MODEL", "qwen3.5:9b")
    llm = get_llm("extraction")
    assert isinstance(llm, ChatOpenAI)
    assert str(llm.openai_api_base).startswith("http://localhost:11434")


def test_all_roles_default_to_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh clone needs only ANTHROPIC_API_KEY (ADR-0015 amendment).
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    for role in ("main", "judge", "fast", "extraction", "vision"):
        assert isinstance(get_llm(role), ChatAnthropic)


def test_gateway_azure_style(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_LLM_BACKEND", "gateway")
    monkeypatch.setenv("SDLCRAG_GATEWAY_BASE_URL", "https://gateway.example.com")
    monkeypatch.setenv("SDLCRAG_GATEWAY_API_KEY", "test-key")
    llm = get_llm("main")
    assert isinstance(llm, AzureChatOpenAI)
    assert llm.deployment_name == get_settings().llm_model


def test_gateway_without_config_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_LLM_BACKEND", "gateway")
    with pytest.raises(RuntimeError, match="GATEWAY_BASE_URL"):
        get_llm("main")


def test_anthropic_api_key_is_used_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_LLM_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    llm = get_llm("main")
    assert isinstance(llm, ChatAnthropic)
    assert llm.anthropic_api_key.get_secret_value() == "sk-test"


def test_anthropic_without_key_resolves_login_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLCRAG_LLM_BACKEND", "anthropic")
    llm = get_llm("main")
    assert isinstance(llm, ChatAnthropic)
    # No static credential pinned, so the SDK falls through to the `ant auth login` profile.
    assert llm._client.api_key is None
