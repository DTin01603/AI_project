"""Configuration management for the RAG system."""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class RAGConfig(BaseModel):
    """Master configuration for RAG system.
    
    This configuration supports loading from environment variables and YAML files,
    with environment variables taking precedence.
    """
    
    # Database
    db_path: str = Field(
        default="data/rag.db",
        description="Path to SQLite database for RAG system"
    )
    
    # Embedding
    embedding_provider: Literal["sentence-transformers", "openai"] = Field(
        default="sentence-transformers",
        description="Embedding model provider"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension"
    )
    
    # Vector Store
    vector_store_type: Literal["chroma", "faiss"] = Field(
        default="chroma",
        description="Vector store backend type"
    )
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
        default=0.3,
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
        default=512,
        ge=100,
        description="Target chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlap between chunks in tokens"
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
    
    # Memory Management
    enable_summarization: bool = Field(
        default=True,
        description="Enable conversation summarization"
    )
    summarization_threshold: int = Field(
        default=50,
        ge=1,
        description="Message count threshold for summarization"
    )
    enable_consolidation: bool = Field(
        default=True,
        description="Enable memory consolidation"
    )
    consolidation_similarity: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for consolidation"
    )
    
    # Cleanup
    cleanup_schedule: str = Field(
        default="0 2 * * *",
        description="Cron schedule for cleanup operations"
    )
    retention_period_days: int = Field(
        default=90,
        ge=1,
        description="Default retention period in days"
    )
    min_importance_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum importance score for retention"
    )
    storage_limit_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Storage limit in GB (None for unlimited)"
    )
    
    # Performance
    max_concurrent_searches: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent search operations"
    )
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
    
    # LLM (optional)
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider for advanced features"
    )
    llm_model: str | None = Field(
        default=None,
        description="LLM model name"
    )
    llm_api_key: str | None = Field(
        default=None,
        description="LLM API key"
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
    
    Args:
        config_path: Path to YAML configuration file (optional)
        env_prefix: Prefix for environment variables (default: "RAG_")
        
    Returns:
        RAGConfig instance with loaded configuration
        
    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If config_path is provided but file doesn't exist
        
    Example:
        # Load from defaults and environment
        config = load_config()
        
        # Load from YAML file
        config = load_config("config/rag.yaml")
        
        # Environment variables override YAML:
        # RAG_DB_PATH=custom.db
        # RAG_EMBEDDING_PROVIDER=openai
    """
    config_dict = {}
    
    # Load from YAML file if provided
    if config_path is not None:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                config_dict.update(yaml_config)
    
    # Override with environment variables
    env_overrides = _load_from_env(env_prefix)
    config_dict.update(env_overrides)
    
    # Create and validate configuration
    config = RAGConfig(**config_dict)
    config.validate_hybrid_weights()
    
    return config


def _load_from_env(prefix: str = "RAG_") -> dict:
    """Load configuration from environment variables.
    
    Args:
        prefix: Environment variable prefix
        
    Returns:
        Dictionary of configuration values from environment
    """
    env_config = {}
    
    # Map of environment variable names to config field names
    env_mapping = {
        f"{prefix}DB_PATH": "db_path",
        f"{prefix}EMBEDDING_PROVIDER": "embedding_provider",
        f"{prefix}EMBEDDING_MODEL": "embedding_model",
        f"{prefix}EMBEDDING_DIMENSION": ("embedding_dimension", int),
        f"{prefix}VECTOR_STORE_TYPE": "vector_store_type",
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
        f"{prefix}ENABLE_SUMMARIZATION": ("enable_summarization", _parse_bool),
        f"{prefix}SUMMARIZATION_THRESHOLD": ("summarization_threshold", int),
        f"{prefix}ENABLE_CONSOLIDATION": ("enable_consolidation", _parse_bool),
        f"{prefix}CONSOLIDATION_SIMILARITY": ("consolidation_similarity", float),
        f"{prefix}CLEANUP_SCHEDULE": "cleanup_schedule",
        f"{prefix}RETENTION_PERIOD_DAYS": ("retention_period_days", int),
        f"{prefix}MIN_IMPORTANCE_THRESHOLD": ("min_importance_threshold", float),
        f"{prefix}STORAGE_LIMIT_GB": ("storage_limit_gb", float),
        f"{prefix}MAX_CONCURRENT_SEARCHES": ("max_concurrent_searches", int),
        f"{prefix}CACHE_SIZE": ("cache_size", int),
        f"{prefix}BATCH_SIZE": ("batch_size", int),
        f"{prefix}LLM_PROVIDER": "llm_provider",
        f"{prefix}LLM_MODEL": "llm_model",
        f"{prefix}LLM_API_KEY": "llm_api_key",
    }
    
    for env_var, field_info in env_mapping.items():
        value = os.getenv(env_var)
        if value is not None:
            # Handle tuple format (field_name, converter)
            if isinstance(field_info, tuple):
                field_name, converter = field_info
                try:
                    env_config[field_name] = converter(value)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid value for {env_var}: {value}. Error: {e}"
                    )
            else:
                # Simple string field
                env_config[field_info] = value
    
    return env_config


def _parse_bool(value: str) -> bool:
    """Parse boolean value from string.
    
    Args:
        value: String value to parse
        
    Returns:
        Boolean value
        
    Raises:
        ValueError: If value cannot be parsed as boolean
    """
    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "on"):
        return True
    elif value_lower in ("false", "0", "no", "off"):
        return False
    else:
        raise ValueError(f"Cannot parse '{value}' as boolean")
