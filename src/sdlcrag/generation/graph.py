"""RAG answer graph (LangGraph): retrieve → generate an answer with inline citations.

The model answers only from numbered sources with inline [n] citations; the cited source
numbers are read from the text. The Mermaid diagram of this graph is generated into the docs by
tools/gen_diagrams.py.
"""

import re
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from sdlcrag.core.models import Answer, Principal, Source
from sdlcrag.providers.llm import get_llm
from sdlcrag.retrieval.retriever import retrieve

SYSTEM = """You answer questions about research on AI in software engineering.
Use ONLY the numbered sources below. Cite every claim inline with its source number, like [2].
If the sources do not contain the answer, say so plainly instead of guessing.
Be concise and specific: name methods, benchmarks, models and numbers when the sources give them."""

CITATION = re.compile(r"\[(\d+)\]")
PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Sources:\n\n{sources}\n\nQuestion: {question}")]
)


class CitedAnswer(BaseModel):
    answer: str = Field(description="The answer, with inline citations like [1], [3].")
    cited: list[int] = Field(description="Numbers of the sources actually used.")


class RagState(BaseModel):
    question: str
    principal: Principal
    sources: list[Source] = Field(default_factory=list)
    answer: CitedAnswer | None = None


def to_sources(docs: list[Document]) -> list[Source]:
    return [
        Source(
            number=i,
            paper_id=str(d.metadata.get("paper_id", "")),
            title=str(d.metadata.get("title", "")),
            section=d.metadata.get("section"),
            page=d.metadata.get("page"),
            url=d.metadata.get("abs_url"),
            license_class=d.metadata.get("license_class"),
            text=d.page_content,
        )
        for i, d in enumerate(docs, 1)
    ]


def format_sources(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[{s.number}] {s.title} (arXiv:{s.paper_id}, {s.section or 'n/a'}, p.{s.page})\n{s.text}"
        for s in sources
    )


def _retrieve(state: RagState) -> dict[str, Any]:
    return {"sources": to_sources(retrieve(state.question, state.principal))}


def _generate(state: RagState) -> dict[str, Any]:
    # Plain text with inline [n] markers: works on every backend (newer Claude models reject
    # the forced tool call that structured output relies on), and the citations are the text.
    chain = PROMPT | get_llm("main") | StrOutputParser()
    text = chain.invoke({"question": state.question, "sources": format_sources(state.sources)})
    valid = {s.number for s in state.sources}
    cited = sorted({int(n) for n in CITATION.findall(text)} & valid)
    return {"answer": CitedAnswer(answer=text, cited=cited)}


def build_rag_graph() -> Any:
    """Compiled LangGraph StateGraph (models are created lazily inside the nodes)."""
    graph = StateGraph(RagState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("generate", _generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def _to_answer(question: str, state: dict[str, Any]) -> Answer:
    cited = CitedAnswer.model_validate(state["answer"])
    return Answer(question=question, text=cited.answer, cited=cited.cited, sources=state["sources"])


def answer(question: str, principal: Principal) -> Answer:
    state = build_rag_graph().invoke(RagState(question=question, principal=principal))
    return _to_answer(question, state)


async def astream_answer(question: str, principal: Principal) -> AsyncIterator[str | Answer]:
    """Stream the answer: text deltas from the generate node (LangGraph `messages` mode),
    then the final `Answer` with its sources and cited numbers."""
    final: dict[str, Any] = {}
    async for mode, payload in build_rag_graph().astream(
        RagState(question=question, principal=principal), stream_mode=["messages", "values"]
    ):
        if mode == "messages":
            chunk, meta = payload
            from_generate = meta.get("langgraph_node") == "generate"
            if isinstance(chunk, AIMessageChunk) and from_generate and chunk.text:
                yield chunk.text
        else:
            final = payload
    yield _to_answer(question, final)
