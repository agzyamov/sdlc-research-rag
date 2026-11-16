"""Chat/vision models per role via LangChain's `init_chat_model` (ADR-0015).

Each role (task) has a backend and a model in ``core.config.Settings``; the backend maps to a
LangChain provider:

- ``local``     → ``openai`` provider pointed at Ollama's OpenAI-compatible API (optional)
- ``gateway``   → ``azure_openai`` or ``openai`` provider pointed at the LLM gateway
- ``anthropic`` → ``anthropic`` provider (API key or `ant auth login` profile)
"""

from typing import TYPE_CHECKING, Any, Literal, cast

import httpx
from langchain.chat_models import init_chat_model

from sdlcrag.core.config import Backend, Settings, get_settings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

Role = Literal["main", "fast", "extraction", "vision", "judge"]


def role_config(role: Role, s: Settings) -> tuple[Backend, str]:
    return {
        "main": (s.llm_backend, s.llm_model),
        "fast": (s.fast_llm_backend, s.fast_llm_model),
        "extraction": (s.extraction_backend, s.extraction_model),
        "vision": (s.vision_backend, s.vision_model),
        "judge": (s.judge_backend, s.judge_model),
    }[role]


def _provider_kwargs(backend: Backend, model: str, s: Settings) -> dict[str, Any]:
    if backend == "local":
        return {"model_provider": "openai", "base_url": s.local_base_url, "api_key": "ollama"}
    if backend == "gateway":
        if not s.gateway_base_url or s.gateway_api_key is None:
            raise RuntimeError(
                "gateway backend selected but SDLCRAG_GATEWAY_BASE_URL / "
                "SDLCRAG_GATEWAY_API_KEY are not set (see .env.example)"
            )
        if s.gateway_api_style == "azure":
            return {
                "model_provider": "azure_openai",
                "azure_endpoint": s.gateway_base_url,
                "azure_deployment": model,
                "api_version": s.gateway_api_version,
                "api_key": s.gateway_api_key,
            }
        return {
            "model_provider": "openai",
            "base_url": s.gateway_base_url,
            "api_key": s.gateway_api_key,
        }
    kwargs: dict[str, Any] = {"model_provider": "anthropic"}
    if s.anthropic_api_key is not None:
        kwargs["api_key"] = s.anthropic_api_key
    return kwargs


def get_llm(role: Role = "main") -> "BaseChatModel":
    """Return the configured chat model for a role."""
    s = get_settings()
    backend, model = role_config(role, s)
    kwargs: dict[str, Any] = {
        **_provider_kwargs(backend, model, s),
        "max_retries": s.llm_max_retries,
        # OpenAI-compatible clients take an httpx.Timeout: a short connect timeout makes an
        # unreachable gateway (e.g. VPN down) fail in seconds, not minutes. ChatAnthropic
        # accepts only a float.
        "timeout": s.llm_timeout_s
        if backend == "anthropic"
        else httpx.Timeout(s.llm_timeout_s, connect=5.0),
    }
    llm = cast("BaseChatModel", init_chat_model(model, **kwargs))
    if backend == "anthropic" and s.anthropic_api_key is None:
        _use_login_profile(llm, s)
    return llm


def _use_login_profile(llm: "BaseChatModel", s: Settings) -> None:
    """langchain-anthropic always passes ``api_key=""`` when no key is set, which the SDK
    treats as an explicit credential and so hides the `ant auth login` profile. Pre-seed its
    cached clients with SDK clients that resolve the named (or active) profile instead."""
    import anthropic

    profile = s.anthropic_profile or None
    retries = getattr(llm, "max_retries", 2)
    llm.__dict__["_client"] = anthropic.Anthropic(max_retries=retries, profile=profile)
    llm.__dict__["_async_client"] = anthropic.AsyncAnthropic(max_retries=retries, profile=profile)
