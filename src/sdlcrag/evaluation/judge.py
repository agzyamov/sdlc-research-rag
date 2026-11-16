"""DeepEval judge model backed by the configured LLM role (gateway Claude by default).

`DeepEvalBaseLLM` is DeepEval's extension point for custom models. When DeepEval asks for a
pydantic `schema`, the call uses schema-constrained output (`json_schema`), which works through
the gateway (forced tool calls are rejected by current Claude models).
"""

from typing import Any

from deepeval.models import DeepEvalBaseLLM

from sdlcrag.providers.llm import Role, get_llm


class GatewayJudge(DeepEvalBaseLLM):
    def __init__(self, role: Role = "judge") -> None:
        self.role: Role = role
        self.chat = get_llm(role)
        super().__init__(model=self.get_model_name())

    def load_model(self, *args: Any, **kwargs: Any) -> Any:
        return self.chat

    def generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        if schema is not None:
            return self.chat.with_structured_output(schema, method="json_schema").invoke(prompt)
        return str(self.chat.invoke(prompt).content)

    async def a_generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        if schema is not None:
            llm = self.chat.with_structured_output(schema, method="json_schema")
            return await llm.ainvoke(prompt)
        return str((await self.chat.ainvoke(prompt)).content)

    def get_model_name(self, *args: Any, **kwargs: Any) -> str:
        return f"sdlcrag-{self.role}"
