"""Configuration management for the RAG system."""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class RAGConfig(BaseModel):
    """Master configuration for RAG system.

    Loads from YAML file and environment variables (env wins).
    """

    # Database
    db_path: str = Field(
        default="data/rag.db",
        description="Path to SQLite database for RAG system"
    )

    # Embedding
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Embedding model name"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension"
    )

    # Vector Store
    vector_store_path: str = Field(
        default="data/vector_store",
        description="Path to vector store data"
    )

    # Search
    default_search_method: Literal["fts", "vector", "hybrid"] = Field(
        default="hybrid",
        description="Default search method"
    )
    fts_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for FTS scores in hybrid search"
    )
    vector_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector scores in hybrid search"
    )
    default_top_k: int = Field(
        default=5,
        ge=1,
        description="Default number of results to return"
    )
    min_relevance_score: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold"
    )

    # Re-ranking
    enable_reranking: bool = Field(
        default=True,
        description="Enable result re-ranking"
    )
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for re-ranking"
    )
    rerank_top_n: int = Field(
        default=100,
        ge=1,
        description="Number of candidates to re-rank"
    )

    # Chunking
    chunk_size: int = Field(
        default=800,
        ge=100,
        description="Target chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=300,
        ge=0,
        description="Overlap between chunks in characters"
    )
    chunking_strategy: Literal["recursive", "semantic", "code-aware"] = Field(
        default="recursive",
        description="Document chunking strategy"
    )

    # Advanced Retrieval
    enable_query_expansion: bool = Field(
        default=False,
        description="Enable query expansion"
    )
    enable_compression: bool = Field(
        default=False,
        description="Enable contextual compression"
    )
    enable_citations: bool = Field(
        default=False,
        description="Enable citation creation and tracking"
    )
    enable_multi_query: bool = Field(
        default=False,
        description="Enable multi-query retrieval"
    )
    query_expansion_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of expanded queries to generate"
    )
    compression_min_ratio: float = Field(
        default=0.2,
        ge=0.2,
        le=0.8,
        description="Minimum contextual compression ratio"
    )
    compression_max_ratio: float = Field(
        default=0.8,
        ge=0.2,
        le=0.8,
        description="Maximum contextual compression ratio"
    )

    # Performance
    cache_size: int = Field(
        default=1000,
        ge=0,
        description="Cache size for embeddings and results"
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        description="Batch size for embedding generation"
    )

    @field_validator("fts_weight", "vector_weight")
    @classmethod
    def validate_weights(cls, v: float, info) -> float:
        """Validate that weights are in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{info.field_name} must be between 0.0 and 1.0")
        return v

    def validate_hybrid_weights(self) -> None:
        """Validate that FTS and vector weights sum to approximately 1.0."""
        total = self.fts_weight + self.vector_weight
        if not 0.99 <= total <= 1.01:
            raise ValueError(
                f"fts_weight ({self.fts_weight}) + vector_weight ({self.vector_weight}) "
                f"should sum to 1.0, got {total}"
            )


def load_config(
    config_path: str | Path | None = None,
    env_prefix: str = "RAG_"
) -> RAGConfig:
    """Load RAG configuration from YAML file and environment variables.

    Configuration priority (highest to lowest):
    1. Environment variables with RAG_ prefix
    2. YAML configuration file
    3. Default values

    Example:
        # Load from defaults and environment
        config = load_config()

        # Load from YAML file
        config = load_config("config/rag.yaml")

        # Environment variables override YAML:
        # RAG_DB_PATH=custom.db
        # RAG_EMBEDDING_MODEL=BAAI/bge-small-en
    """
    config_dict = {}

    if config_path is not None:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                config_dict.update(yaml_config)

    env_overrides = _load_from_env(env_prefix)
    config_dict.update(env_overrides)

    config = RAGConfig(**config_dict)
    config.validate_hybrid_weights()

    return config


def _load_from_env(prefix: str = "RAG_") -> dict:
    """Load configuration from environment variables."""
    env_config: dict = {}

    # Each entry: env var name -> field name (string) or (field name, converter)
    env_mapping: dict[str, str | tuple[str, type]] = {
        f"{prefix}DB_PATH": "db_path",
        f"{prefix}EMBEDDING_MODEL": "embedding_model",
        f"{prefix}EMBEDDING_DIMENSION": ("embedding_dimension", int),
        f"{prefix}VECTOR_STORE_PATH": "vector_store_path",
        f"{prefix}DEFAULT_SEARCH_METHOD": "default_search_method",
        f"{prefix}FTS_WEIGHT": ("fts_weight", float),
        f"{prefix}VECTOR_WEIGHT": ("vector_weight", float),
        f"{prefix}DEFAULT_TOP_K": ("default_top_k", int),
        f"{prefix}MIN_RELEVANCE_SCORE": ("min_relevance_score", float),
        f"{prefix}ENABLE_RERANKING": ("enable_reranking", _parse_bool),
        f"{prefix}RERANKER_MODEL": "reranker_model",
        f"{prefix}RERANK_TOP_N": ("rerank_top_n", int),
        f"{prefix}CHUNK_SIZE": ("chunk_size", int),
        f"{prefix}CHUNK_OVERLAP": ("chunk_overlap", int),
        f"{prefix}CHUNKING_STRATEGY": "chunking_strategy",
        f"{prefix}ENABLE_QUERY_EXPANSION": ("enable_query_expansion", _parse_bool),
        f"{prefix}ENABLE_COMPRESSION": ("enable_compression", _parse_bool),
        f"{prefix}ENABLE_CITATIONS": ("enable_citations", _parse_bool),
        f"{prefix}ENABLE_MULTI_QUERY": ("enable_multi_query", _parse_bool),
        f"{prefix}QUERY_EXPANSION_COUNT": ("query_expansion_count", int),
        f"{prefix}COMPRESSION_MIN_RATIO": ("compression_min_ratio", float),
        f"{prefix}COMPRESSION_MAX_RATIO": ("compression_max_ratio", float),
        f"{prefix}CACHE_SIZE": ("cache_size", int),
        f"{prefix}BATCH_SIZE": ("batch_size", int),
    }

    for env_var, field_info in env_mapping.items():
        value = os.getenv(env_var)
        if value is None:
            continue
        if isinstance(field_info, tuple):
            field_name, converter = field_info
            try:
                env_config[field_name] = converter(value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid value for {env_var}: {value}. Error: {e}")
        else:
            env_config[field_info] = value

    return env_config


def _parse_bool(value: str) -> bool:
    """Parse boolean value from string."""
    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "on"):
        return True
    if value_lower in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"Cannot parse '{value}' as boolean")
