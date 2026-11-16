"""Figure descriptions via Docling's built-in picture description (multimodal RAG).

During PDF conversion Docling sends each figure (above an area threshold, so logos and icons
are skipped) to an OpenAI-compatible vision endpoint and stores the reply as an annotation.
Docling's chunking serializer includes those annotations in the chunk text, so figures become
searchable like any other content (`modality=image`).
"""

import logging

import httpx
from docling.datamodel.pipeline_options import PictureDescriptionApiOptions

from sdlcrag.core.config import get_settings

log = logging.getLogger(__name__)

PROMPT = (
    "This figure is from a software engineering research paper. Describe it for search: "
    "what kind of figure it is (architecture diagram, workflow, results chart, table, example), "
    "its main components and labels, and any key numbers, comparisons or trends. "
    "3 to 5 factual sentences, no speculation."
)


def picture_description_options() -> PictureDescriptionApiOptions | None:
    """Docling options for the configured vision backend, or None when figures are off."""
    s = get_settings()
    if not s.describe_figures:
        return None
    if s.vision_backend == "gateway":
        if not s.gateway_base_url or s.gateway_api_key is None:
            log.warning("figure descriptions off: gateway URL/key not configured")
            return None
        base = s.gateway_base_url.rstrip("/")
        key = s.gateway_api_key.get_secret_value()
        if s.gateway_api_style == "azure":
            url = (
                f"{base}/openai/deployments/{s.vision_model}/chat/completions"
                f"?api-version={s.gateway_api_version}"
            )
            headers = {"Api-Key": key}
        else:
            url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {key}"}
    elif s.vision_backend == "local":
        url, headers = f"{s.local_base_url.rstrip('/')}/chat/completions", {}
    else:  # the Anthropic Messages API is not OpenAI-compatible
        log.warning("figure descriptions need the gateway or local backend; skipping")
        return None
    return PictureDescriptionApiOptions(
        url=url,  # pyrefly: ignore[bad-argument-type]  (pydantic coerces str to AnyUrl)
        headers=headers,
        # Without reasoning_effort=low, current Claude models spend the whole output budget
        # on reasoning and return an empty description.
        params={"model": s.vision_model, "max_tokens": 600, "reasoning_effort": "low"},
        prompt=PROMPT,
        timeout=60,
        concurrency=4,
        picture_area_threshold=s.figure_area_threshold,
    )


def ensure_vision_reachable(options: PictureDescriptionApiOptions | None) -> None:
    """Fail fast if the vision endpoint can't be reached.

    Docling logs failed description calls and carries on, which would index a paper without its
    figure descriptions and mark it done. Raising a network error instead makes the paper fail
    as retryable (the orchestrator retries network errors).
    """
    if options is None:
        return
    url = httpx.URL(str(options.url))
    with httpx.Client(timeout=5) as client:
        client.head(f"{url.scheme}://{url.host}")  # any HTTP response means reachable
