"""RAG (Retrieval-Augmented Generation) system for the research agent."""

from .config import RAGConfig, load_config
from .chunking import Chunk, ChunkingStrategy, CodeAwareChunking, RecursiveCharacterChunking
from .contextual_compressor import CompressionResult, ContextualCompressor
from .citation_tracker import Citation, CitationTracker
from .document_indexer import DocumentIndexer, IndexingResult
from .document_loader import (
    DOCXLoader,
    PDFLoader,
    CodeLoader,
    Document,
    DocumentLoadError,
    DocumentLoader,
    DocumentMetadata,
    MarkdownLoader,
    TextLoader,
    get_default_loaders,
    load_document,
)
from .embedding import EmbeddingModel, OpenAIEmbedding, SentenceTransformerEmbedding
from .fts_engine import FTSEngine, SearchResult
from .hybrid_search import HybridSearchEngine
from .metrics import RAGMetrics, RetrievalMetrics, get_metrics, reset_metrics
from .multi_query_retriever import MultiQueryResult, MultiQueryRetriever
from .query_expander import QueryExpander
from .reranker import ReRanker
from .vector_store import ChromaVectorStore, VectorStore

__all__ = [
    "RAGConfig",
    "load_config",
    "Document",
    "DocumentMetadata",
    "DocumentLoader",
    "DocumentLoadError",
    "PDFLoader",
    "DOCXLoader",
    "MarkdownLoader",
    "CodeLoader",
    "TextLoader",
    "get_default_loaders",
    "load_document",
    "Chunk",
    "ChunkingStrategy",
    "RecursiveCharacterChunking",
    "CodeAwareChunking",
    "ContextualCompressor",
    "CompressionResult",
    "Citation",
    "CitationTracker",
    "DocumentIndexer",
    "IndexingResult",
    "EmbeddingModel",
    "SentenceTransformerEmbedding",
    "OpenAIEmbedding",
    "FTSEngine",
    "SearchResult",
    "VectorStore",
    "ChromaVectorStore",
    "HybridSearchEngine",
    "QueryExpander",
    "MultiQueryRetriever",
    "MultiQueryResult",
    "ReRanker",
    "RAGMetrics",
    "RetrievalMetrics",
    "get_metrics",
    "reset_metrics",
]
