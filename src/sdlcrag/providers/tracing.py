"""Langfuse callback wiring (ADR-0009). Returns no callbacks when Langfuse isn't configured."""

import os
from typing import Any


def tracing_callbacks() -> list[Any]:
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]
