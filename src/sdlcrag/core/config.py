"""Application settings. The single source of configuration (env prefix ``SDLCRAG_``)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Backend = Literal["local", "gateway", "anthropic"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SDLCRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM backends (ADR-0015). Each task (role) picks a backend and a model:
    #   local:     Ollama on this machine (OpenAI-compatible API), optional: free / offline
    #   gateway:   an OpenAI/Azure-compatible LLM gateway (URL and key only in .env)
    #   anthropic: Claude API directly (API key or `ant auth login` profile)
    local_base_url: str = "http://localhost:11434/v1"
    gateway_base_url: str | None = None
    gateway_api_key: SecretStr | None = None
    gateway_api_style: Literal["azure", "openai"] = "azure"
    gateway_api_version: str = "2024-10-21"

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "SDLCRAG_ANTHROPIC_API_KEY"),
    )
    anthropic_profile: str | None = None  # named `ant auth login` profile

    # Role → backend + model (ADR-0015). Default: everything through the gateway, with a
    # cheap model for bulk roles. Set a bulk role's backend to "local" for $0 / offline runs.
    llm_backend: Backend = "anthropic"  # final answers with citations
    llm_model: str = "claude-sonnet-5-5"
    judge_backend: Backend = "anthropic"  # evaluation judge (independent of local models)
    judge_model: str = "claude-sonnet-5-5"
    fast_llm_backend: Backend = "anthropic"  # relevance grading, query rewriting
    fast_llm_model: str = "claude-haiku-5-5"
    extraction_backend: Backend = "anthropic"  # paper facts (abstract-first)
    extraction_model: str = "claude-haiku-5-5"
    vision_backend: Backend = "anthropic"  # figure descriptions
    vision_model: str = "claude-haiku-5-5"

    # Cost controls: ADR-0014
    use_batch_api: bool = True  # Message Batches (-50%); only applies to the anthropic backend
    llm_cache: bool = True  # on-disk cache keyed by (model, prompt version, content hash)
    describe_figures: bool = True  # Docling picture description via the vision role
    figure_area_threshold: float = 0.05  # min share of the page area; skips logos and icons
    answer_max_tokens: int = 2048
    llm_timeout_s: float = 180.0  # per request (long-context baseline prompts are large)
    llm_max_retries: int = 2
    max_cost_usd: float | None = None  # hard stop per run; None = no limit (use --max-cost)

    # arXiv: ADR-0013 (fair use: <= 1 request / 3 s)
    http_user_agent: str = "sdlcrag/0.1 (research RAG; +https://arxiv.org/help/api)"
    arxiv_min_interval_s: float = 3.0

    # Embeddings / reranker: ADR-0005, ADR-0006
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    sparse_model: str = "Qdrant/bm25"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    device: str = "mps"

    # Qdrant: ADR-0004
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"

    # Neo4j knowledge graph + neo4j-graphrag entity resolution: ADR-0018
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("sdlcrag-dev")
    neo4j_database: str = "neo4j"
    # RapidFuzz WRatio (0..1). Below ~0.95 it merges substrings ("LLM" into "LLM agents").
    entity_similarity_threshold: float = 0.95

    # OpenFGA: ADR-0007
    openfga_api_url: str = "http://localhost:8080"
    openfga_store_id: str | None = None
    openfga_model_id: str | None = None

    # Retrieval
    retrieval_candidates: int = 40
    retrieval_top_k: int = 6

    # Paths
    data_dir: Path = Path("data")
    eval_dir: Path = Path("eval")

    @property
    def golden_path(self) -> Path:
        return self.eval_dir / "golden_qa.jsonl"

    @property
    def reports_dir(self) -> Path:
        return self.eval_dir / "reports"

    @property
    def llm_cache_dir(self) -> Path:
        return self.data_dir / "cache" / "llm"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def record_manager_db_url(self) -> str:
        """LangChain RecordManager (content hashes per chunk, grouped by paper)."""
        return f"sqlite:///{self.data_dir / 'index' / 'record_manager.sqlite'}"

    @property
    def dagster_home(self) -> Path:
        """Dagster instance (run history, partition status, asset values); gitignored."""
        return Path(".dagster").resolve()

    @property
    def corpus_path(self) -> Path:
        return self.data_dir / "corpus.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
