# Core-Only Implementation Plan: RAG Tool (MVP)

## Goal
Deliver a simple, usable RAG system for chat/research with:
- conversation retrieval
- document indexing
- hybrid search quality
- stable API behavior

This plan intentionally removes non-core and production-heavy items.

## Scope In
- SQLite FTS search for conversation memory
- Embedding + vector search
- Hybrid retrieval (FTS + vector)
- Basic re-ranking
- Document loaders + chunking + indexing
- Multi-source retrieval (conversation + document/code)
- Lightweight advanced retrieval (query expansion, optional compression/citation)
- Essential unit/integration tests

## Scope Out (deferred)
- Full memory lifecycle engine (importance scoring, cleanup policy, scheduler)
- Large property-based test matrix (49 properties)
- FAISS backend, OpenAI embedding production integration
- Complex observability/security/migration hardening beyond current MVP needs

---

## Phase A: Search Foundation (Core)

- [x] 1. Core config and project structure
  - [x] Define `RAGConfig` and loading from env/YAML
  - [x] Create base RAG package and test structure

- [x] 2. SQLite FTS retrieval
  - [x] Create FTS table + triggers
  - [x] Implement FTSEngine (`index_message`, `search`, `delete_message`)
  - [x] Add FTS unit/property sanity tests

- [x] 3. Retrieval node integration
  - [x] Integrate retrieval into LangGraph node flow
  - [x] Add retrieval metrics/logging
  - [x] Add RetrievalNode unit tests

- [x] 4. Search API
  - [x] POST `/api/search`
  - [x] GET `/api/search/health`
  - [x] Input validation, pagination, execution-time header
  - [x] Integration tests for API flow

---

## Phase B: Hybrid Search (Core)

- [x] 5. Embedding model
  - [x] `EmbeddingModel` interface
  - [x] SentenceTransformer implementation
  - [x] Embedding cache
  - [x] Unit tests

- [x] 6. Vector store
  - [x] `VectorStore` interface
  - [x] Chroma-backed implementation (with local fallback)
  - [x] Unit tests

- [x] 7. Hybrid search + reranking
  - [x] Parallel FTS/vector retrieval
  - [x] Weighted merge + dedupe + graceful fallback
  - [x] ReRanker with cosine fallback
  - [x] Hybrid/retrieval integration tests

---

## Phase C: Document Indexing (Core)

- [x] 8. Document loading
  - [x] Support: txt, md, pdf, docx, code (py/js/ts/java)
  - [x] Metadata extraction + loader error handling
  - [x] Unit tests

- [x] 9. Chunking strategy
  - [x] Recursive chunking
  - [x] Code-aware chunking
  - [x] Unit tests

- [x] 10. Indexing pipeline
  - [x] Load -> chunk -> embed -> store
  - [x] Store document metadata in SQLite
  - [x] Integration tests

- [x] 11. Multi-source retrieval
  - [x] Query conversation + document sources
  - [x] Source filtering + unified merge
  - [x] Graceful degradation
  - [x] Unit/integration coverage

---

## Phase D: Lightweight Quality Boost (Core-Plus)

- [x] 12. Query expansion
  - [x] Rule-based + optional WordNet expansion
  - [x] Timeout + cache + dedupe
  - [x] Integrate into HybridSearchEngine
  - [x] Unit/integration tests

- [x] 13. Multi-query retrieval
  - [x] Rule-based decomposition
  - [x] Parallel sub-query retrieval + aggregation
  - [x] Attribution metadata
  - [x] Unit tests

- [x] 14. Optional response-quality features
  - [x] Contextual compression
  - [x] Citation tracking + formatting
  - [x] RetrievalNode integration toggles
  - [x] Unit/integration tests

---

## Final Core Exit Criteria

- [x] 15. Core regression suite green
  - [x] Run key retrieval + API integration tests
  - [x] Confirm no break on conversation-only mode

- [x] 16. Core documentation pass
  - [x] Update README with current core architecture
  - [x] Add 3 usage examples: FTS, hybrid, document indexing

- [x] 17. Core release checkpoint
  - [x] Validate end-to-end behavior on representative dataset
  - [x] Freeze MVP scope and defer non-core roadmap

---

## Deferred Backlog (Explicitly Out of MVP)

- Property tests not required for MVP confidence
- Memory management phase (importance, cleanup, scheduling)
- Full security/rate-limit/auth hardening
- Full migration/versioning framework
- Full observability/perf benchmark suite at large scale
