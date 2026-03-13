"""Unit tests for RAG configuration."""

import os
import tempfile

import pytest
import yaml

from rag.config import RAGConfig, load_config, _parse_bool


class TestRAGConfig:
    """Test RAGConfig model validation."""

    def test_default_config(self):
        """Test that default configuration is valid."""
        config = RAGConfig()

        assert config.db_path == "data/rag.db"
        assert config.embedding_provider == "sentence-transformers"
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.embedding_dimension == 384
        assert config.vector_store_type == "chroma"
        assert config.default_search_method == "hybrid"
        assert config.fts_weight == 0.3
        assert config.vector_weight == 0.7
        assert config.default_top_k == 5
        assert config.min_relevance_score == 0.3

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = RAGConfig(
            db_path="custom.db",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimension=1536,
            vector_store_type="faiss",
            default_search_method="vector",
            fts_weight=0.4,
            vector_weight=0.6,
            default_top_k=10,
            min_relevance_score=0.5,
        )

        assert config.db_path == "custom.db"
        assert config.embedding_provider == "openai"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimension == 1536
        assert config.vector_store_type == "faiss"
        assert config.default_search_method == "vector"
        assert config.fts_weight == 0.4
        assert config.vector_weight == 0.6
        assert config.default_top_k == 10
        assert config.min_relevance_score == 0.5

    def test_weight_validation(self):
        """Test that weights are validated to be in [0, 1] range."""
        config = RAGConfig(fts_weight=0.0, vector_weight=1.0)
        assert config.fts_weight == 0.0
        assert config.vector_weight == 1.0

        with pytest.raises(ValueError):
            RAGConfig(fts_weight=-0.1, vector_weight=1.1)

        with pytest.raises(ValueError):
            RAGConfig(fts_weight=1.5, vector_weight=0.5)

    def test_hybrid_weights_validation(self):
        """Test that hybrid search weights sum to approximately 1.0."""
        config = RAGConfig(fts_weight=0.3, vector_weight=0.7)
        config.validate_hybrid_weights()

        config_invalid = RAGConfig(fts_weight=0.5, vector_weight=0.3)
        with pytest.raises(ValueError, match="should sum to 1.0"):
            config_invalid.validate_hybrid_weights()

    def test_field_constraints(self):
        """Test that field constraints are enforced."""
        with pytest.raises(ValueError):
            RAGConfig(default_top_k=0)

        with pytest.raises(ValueError):
            RAGConfig(chunk_size=50)

        with pytest.raises(ValueError):
            RAGConfig(chunk_overlap=-1)

        config = RAGConfig(default_top_k=1, chunk_size=100, chunk_overlap=0)
        assert config.default_top_k == 1
        assert config.chunk_size == 100
        assert config.chunk_overlap == 0


class TestLoadConfig:
    """Test configuration loading from files and environment."""

    def test_load_default_config(self):
        """Test loading config with defaults only."""
        config = load_config()

        assert isinstance(config, RAGConfig)
        assert config.db_path == "data/rag.db"
        assert config.embedding_provider == "sentence-transformers"

    def test_load_from_yaml(self):
        """Test loading config from YAML file."""
        yaml_content = {
            "db_path": "yaml_test.db",
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_dimension": 1536,
            "default_top_k": 10,
            "fts_weight": 0.4,
            "vector_weight": 0.6,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            yaml.dump(yaml_content, temp_file)
            yaml_path = temp_file.name

        try:
            config = load_config(yaml_path)

            assert config.db_path == "yaml_test.db"
            assert config.embedding_provider == "openai"
            assert config.embedding_model == "text-embedding-3-small"
            assert config.embedding_dimension == 1536
            assert config.default_top_k == 10
            assert config.fts_weight == 0.4
            assert config.vector_weight == 0.6
        finally:
            os.unlink(yaml_path)

    def test_load_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("RAG_DB_PATH", "env_test.db")
        monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("RAG_EMBEDDING_DIMENSION", "1536")
        monkeypatch.setenv("RAG_DEFAULT_TOP_K", "15")
        monkeypatch.setenv("RAG_FTS_WEIGHT", "0.25")
        monkeypatch.setenv("RAG_VECTOR_WEIGHT", "0.75")
        monkeypatch.setenv("RAG_ENABLE_RERANKING", "false")

        config = load_config()

        assert config.db_path == "env_test.db"
        assert config.embedding_provider == "openai"
        assert config.embedding_dimension == 1536
        assert config.default_top_k == 15
        assert config.fts_weight == 0.25
        assert config.vector_weight == 0.75
        assert config.enable_reranking is False

    def test_env_overrides_yaml(self, monkeypatch):
        """Test that environment variables override YAML config."""
        yaml_content = {
            "db_path": "yaml.db",
            "embedding_provider": "sentence-transformers",
            "default_top_k": 5,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            yaml.dump(yaml_content, temp_file)
            yaml_path = temp_file.name

        try:
            monkeypatch.setenv("RAG_DB_PATH", "env.db")
            monkeypatch.setenv("RAG_DEFAULT_TOP_K", "20")

            config = load_config(yaml_path)

            assert config.db_path == "env.db"
            assert config.default_top_k == 20
            assert config.embedding_provider == "sentence-transformers"
        finally:
            os.unlink(yaml_path)

    def test_load_nonexistent_file(self):
        """Test that loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_invalid_env_values(self, monkeypatch):
        """Test that invalid environment values raise errors."""
        monkeypatch.setenv("RAG_DEFAULT_TOP_K", "not_a_number")

        with pytest.raises(ValueError, match="Invalid value"):
            load_config()


class TestParseBool:
    """Test boolean parsing from strings."""

    def test_parse_true_values(self):
        """Test parsing various true values."""
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("on") is True
        assert _parse_bool("ON") is True

    def test_parse_false_values(self):
        """Test parsing various false values."""
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("FALSE") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False
        assert _parse_bool("No") is False
        assert _parse_bool("off") is False
        assert _parse_bool("OFF") is False

    def test_parse_invalid_values(self):
        """Test that invalid values raise errors."""
        with pytest.raises(ValueError):
            _parse_bool("maybe")

        with pytest.raises(ValueError):
            _parse_bool("2")

        with pytest.raises(ValueError):
            _parse_bool("")