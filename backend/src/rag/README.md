# RAG System (Core MVP)

This package provides a practical RAG pipeline for chat and research flows:

- conversation retrieval (SQLite FTS + vector)
- document and code indexing (load -> chunk -> embed -> store)
- hybrid ranking (FTS + vector merge + optional reranking)
- optional quality boosts (query expansion, multi-query, compression, citation)

## Core architecture

Main components:

- `fts_engine.py`: keyword retrieval over conversation messages in SQLite FTS.
- `embedding.py`: embedding model interface and sentence-transformer implementation.
- `vector_store.py`: conversation/document vector retrieval with metadata filtering.
- `hybrid_search.py`: parallel FTS/vector retrieval and weighted merge.
- `document_loader.py`: loaders for `txt`, `md`, `pdf`, `docx`, and code files.
- `chunking.py`: recursive and code-aware chunking.
- `document_indexer.py`: document indexing pipeline and metadata persistence.
- `retrieval_node.py`: LangGraph integration entry point for search/retrieval.

## Configuration

Config is loaded in this order:

1. Environment variables (`RAG_` prefix)
2. YAML file (for example `backend/config/rag.yaml`)
3. `RAGConfig` defaults

Core env vars:

```bash
RAG_DB_PATH=data/rag.db
RAG_VECTOR_STORE_PATH=data/vector_store
RAG_DEFAULT_SEARCH_METHOD=hybrid
RAG_FTS_WEIGHT=0.3
RAG_VECTOR_WEIGHT=0.7
RAG_DEFAULT_TOP_K=5
RAG_MIN_RELEVANCE_SCORE=0.3

RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50
RAG_CHUNKING_STRATEGY=recursive

# Core-plus features are disabled by default in MVP
RAG_ENABLE_QUERY_EXPANSION=false
RAG_ENABLE_MULTI_QUERY=false
RAG_ENABLE_COMPRESSION=false
RAG_ENABLE_CITATIONS=false
```

## Usage examples

### 1) FTS retrieval (conversation only)

```python
from rag.fts_engine import FTSEngine

fts = FTSEngine(db_path="data/rag.db")
results = fts.search(
	query="docker compose",
	top_k=5,
	min_score=0.1,
	filters={"conversation_id": "conv-123"},
)

for row in results:
	print(row.id, row.score, row.content[:80])
```

### 2) Hybrid retrieval (FTS + vector)

```python
from rag.config import RAGConfig
from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from rag.hybrid_search import HybridSearchEngine
from rag.vector_store import ChromaVectorStore

cfg = RAGConfig()
fts = FTSEngine(db_path=cfg.db_path)
embedder = SentenceTransformerEmbedding(
	model_name=cfg.embedding_model,
	dimension=cfg.embedding_dimension,
)
conversation_store = ChromaVectorStore(
	persist_directory=cfg.vector_store_path,
	collection_name="conversation_messages",
)
document_store = ChromaVectorStore(
	persist_directory=cfg.vector_store_path,
	collection_name="indexed_documents",
)

engine = HybridSearchEngine(
	fts_engine=fts,
	vector_store=conversation_store,
	embedding_model=embedder,
	document_vector_store=document_store,
	fts_weight=cfg.fts_weight,
	vector_weight=cfg.vector_weight,
)

results = engine.search(
	query="how to deploy backend",
	top_k=5,
	min_score=0.2,
	filters={"source_types": ["conversation", "document"]},
)
```

### 3) Document indexing

```python
from rag.config import RAGConfig
from rag.document_indexer import DocumentIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore

cfg = RAGConfig()
embedder = SentenceTransformerEmbedding(
	model_name=cfg.embedding_model,
	dimension=cfg.embedding_dimension,
)
doc_store = ChromaVectorStore(
	persist_directory=cfg.vector_store_path,
	collection_name="indexed_documents",
)

indexer = DocumentIndexer(
	db_path=cfg.db_path,
	embedding_model=embedder,
	vector_store=doc_store,
	config=cfg,
)

result = indexer.index_file("docs/setup_guide.md")
print(result.document_id, result.chunk_count)
```

## Core validation commands

Run the core integration suite used for MVP exit:

```bash
cd backend
pytest tests/integration/test_retrieval_with_metrics.py \
  tests/integration/test_hybrid_retrieval_node.py \
  tests/integration/test_document_indexing_retrieval.py \
  tests/integration/test_query_expansion_integration.py \
  tests/integration/test_search_api.py -q
```

## Notes

- Conversation-only mode is supported through retrieval filters such as
  `{"source_type": "conversation"}`.
- Non-core hardening work is intentionally deferred in the MVP plan at
  `.kiro/specs/rag-tool-implementation/tasks.md`.
